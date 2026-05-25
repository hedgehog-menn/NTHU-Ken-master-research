"""Smoke test: run the notebook pipeline against uploaded sample to catch bugs before user runs it."""
import json
from pathlib import Path
from collections import defaultdict
from itertools import combinations

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
import networkx as nx
from sklearn.metrics import roc_auc_score

DATA_DIR = Path('./Karin_dataset/')
# POSTS_FILE = DATA_DIR / '00_Datasets-sample.txt'
POSTS_FILE = DATA_DIR / '00_Datasets.txt'
SOCK_MASTER = DATA_DIR / '01_SockpuppetGroup.txt'
NORM_MASTER = DATA_DIR / '02_NormalGroup.txt'

SPLIT_FILES = {
    1: {'train_sock': '03_First_Train_Sock.txt', 'test_sock': '03_First_Test_Sock.txt',
        'train_normal': '03_First_Train_Normal.txt', 'test_normal': '03_First_Test_Normal.txt'},
    2: {'train_sock': '04_Second_Train_Sock.txt', 'test_sock': '04_Second_Test_Sock.txt',
        'train_normal': '04_Second_Train_Normal.txt', 'test_normal': '04_Second_Test_Normal.txt'},
    3: {'train_sock': '05_Third_Train_Sock.txt', 'test_sock': '05_Third_Test_Sock.txt',
        'train_normal': '05_Third_Train_Normal.txt', 'test_normal': '05_Third_Test_Normal.txt'},
}
SPLIT_FILES = {e: {k: DATA_DIR / v for k, v in d.items()} for e, d in SPLIT_FILES.items()}

TIME_WINDOWS_MIN = [30, 120, 360]
MIN_SHARED_THREADS = 1
MAX_USERS_PER_THREAD = 300
RANDOM_SEED = 42

def load_json(p):
    with open(p, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

np.random.seed(RANDOM_SEED)
print('=== Cell 2: Load posts ===')
records = load_json(POSTS_FILE)
posts = pd.DataFrame(records)
posts['user_id'] = posts['user_id'].astype(int)
posts['thread_id'] = posts['thread_id'].astype(int)
posts['datetime'] = pd.to_datetime(posts['datetime'], format='%m/%d/%Y %H:%M:%S')
posts = posts.sort_values(['thread_id', 'datetime']).reset_index(drop=True)
print(f'Posts: {len(posts):,}  Users: {posts.user_id.nunique():,}  Threads: {posts.thread_id.nunique():,}')

print('\n=== Cell 3: Labels & splits ===')
sock_groups_master = load_json(SOCK_MASTER)
norm_groups_master = load_json(NORM_MASTER)
sock_users_master = {u for g in sock_groups_master for u in g}
norm_users_master = {u for g in norm_groups_master for u in g}
label_map = {u: 1 for u in sock_users_master}
label_map.update({u: 0 for u in norm_users_master})
print(f'Labeled users: {len(label_map)}')

user_to_group = {}
for gid, members in enumerate(sock_groups_master):
    for u in members:
        user_to_group[u] = f'sock_{gid}'
for gid, members in enumerate(norm_groups_master):
    for u in members:
        user_to_group[u] = f'norm_{gid}'

def load_split(exp_id):
    sp = SPLIT_FILES[exp_id]
    ts = {u for g in load_json(sp['train_sock']) for u in g}
    es = {u for g in load_json(sp['test_sock']) for u in g}
    tn = {u for g in load_json(sp['train_normal']) for u in g}
    en = {u for g in load_json(sp['test_normal']) for u in g}
    tr, te = ts | tn, es | en
    assert not (tr & te)
    return dict(train_users=tr, test_users=te, train_sock=ts, test_sock=es,
                train_normal=tn, test_normal=en)

splits = {e: load_split(e) for e in (1, 2, 3)}
for e, s in splits.items():
    print(f'Exp {e}: train={len(s["train_users"])} test={len(s["test_users"])}')

print('\n=== Cell 4: Build indexes ===')
user_activity = defaultdict(list)
thread_activity = defaultdict(list)
for row in posts.itertuples(index=False):
    user_activity[row.user_id].append((row.thread_id, row.datetime))
    thread_activity[row.thread_id].append((row.user_id, row.datetime))
for uid in user_activity:
    user_activity[uid].sort(key=lambda x: x[1])
for tid in thread_activity:
    thread_activity[tid].sort(key=lambda x: x[1])
print(f'Users in index: {len(user_activity):,}  Threads in index: {len(thread_activity):,}')
labeled_in_posts = set(user_activity) & set(label_map)
print(f'Labeled users with posts: {len(labeled_in_posts)} / {len(label_map)}')

print('\n=== Cell 5: Pair stats ===')
pair_stats = {}
n_truncated = 0
for tid, events in thread_activity.items():
    user_first = {}
    for uid, ts in events:
        if uid not in user_first:
            user_first[uid] = ts
    if len(user_first) > MAX_USERS_PER_THREAD:
        items = sorted(user_first.items(), key=lambda kv: kv[1])[:MAX_USERS_PER_THREAD]
        user_first = dict(items)
        n_truncated += 1
    users = sorted(user_first)
    for u1, u2 in combinations(users, 2):
        gap = abs((user_first[u1] - user_first[u2]).total_seconds())
        key = (u1, u2)
        s = pair_stats.get(key)
        if s is None:
            pair_stats[key] = {'n_threads': 1, 'min_gaps_sec': [gap]}
        else:
            s['n_threads'] += 1
            s['min_gaps_sec'].append(gap)
print(f'Raw pairs: {len(pair_stats):,}  Truncated threads: {n_truncated}')
pair_stats = {k: v for k, v in pair_stats.items() if v['n_threads'] >= MIN_SHARED_THREADS}
print(f'After min_shared filter: {len(pair_stats):,}')

print('\n=== Cell 6: Build adjacency ===')
graph_users = sorted({u for pair in pair_stats for u in pair})
u2i = {u: i for i, u in enumerate(graph_users)}
N = len(graph_users)
print(f'Graph users: {N:,}')

def build_adj(window_seconds=None):
    rows, cols, vals = [], [], []
    for (u1, u2), s in pair_stats.items():
        if window_seconds is None:
            w = s['n_threads']
        else:
            w = sum(1 for g in s['min_gaps_sec'] if g <= window_seconds)
        if w < MIN_SHARED_THREADS:
            continue
        i, j = u2i[u1], u2i[u2]
        rows += [i, j]; cols += [j, i]; vals += [w, w]
    return csr_matrix((vals, (rows, cols)), shape=(N, N), dtype=np.float32)

adj_all = build_adj(None)
adj_windows = {w: build_adj(w * 60) for w in TIME_WINDOWS_MIN}
print(f'Edges (all): {adj_all.nnz // 2:,}')
for w, A in adj_windows.items():
    print(f'Edges ({w} min): {A.nnz // 2:,}')

print('\n=== Cell 7: Label-free features ===')
def degrees(A):
    return np.asarray(A.sum(axis=1)).ravel()

feat = pd.DataFrame({'user_id': graph_users})
feat['deg_all'] = degrees(adj_all)
for w, A in adj_windows.items():
    feat[f'deg_w{w}'] = degrees(A)

edge_weights = np.array(adj_all[adj_all.nonzero()]).ravel()
p90 = float(np.percentile(edge_weights, 90)) if len(edge_weights) else 0.0
strong = (adj_all >= p90).astype(np.int8)
feat['n_strong_neighbors'] = np.asarray(strong.sum(axis=1)).ravel()
feat['top_neighbor_weight'] = np.asarray(adj_all.max(axis=1).todense()).ravel()

G_bin = nx.from_scipy_sparse_array((adj_all > 0).astype(np.int8))
clust = nx.clustering(G_bin)
feat['clustering_coef'] = feat.index.map(lambda i: clust.get(i, 0.0)).astype(float)

deg_vec = feat['deg_all'].values
A_lil = adj_all.tolil()
mean_nb = np.zeros(N)
for i in range(N):
    nbrs = A_lil.rows[i]
    if nbrs:
        mean_nb[i] = deg_vec[nbrs].mean()
feat['mean_neighbor_degree'] = mean_nb

tightest = min(TIME_WINDOWS_MIN)
feat['temporal_concentration'] = (
    feat[f'deg_w{tightest}'] / feat['deg_all'].replace(0, np.nan)
).fillna(0)
print(feat.describe().round(2))

print('\n=== Cell 8: Label-dependent features per experiment ===')
def compute_label_dependent(feat_base, exp_split, label_map_in):
    train_users = exp_split['train_users']
    train_positive = np.zeros(N, dtype=np.float32)
    train_known = np.zeros(N, dtype=np.float32)
    for i, uid in enumerate(graph_users):
        if uid in train_users:
            train_known[i] = 1.0
            if label_map_in.get(uid, 0) == 1:
                train_positive[i] = 1.0
    neighbor_pos = adj_all.dot(train_positive)
    neighbor_known = adj_all.dot(train_known)
    ratio = np.divide(neighbor_pos, neighbor_known,
                      out=np.zeros_like(neighbor_pos), where=neighbor_known > 0)
    out = feat_base.copy()
    out['neighbor_sockpuppet_ratio'] = ratio
    out['n_known_train_neighbors'] = neighbor_known
    out['n_positive_train_neighbors'] = neighbor_pos
    return out

OUT_DIR = Path('./smoke_test_output/'); OUT_DIR.mkdir(exist_ok=True)
for exp in (1, 2, 3):
    s = splits[exp]
    feat_exp = compute_label_dependent(feat, s, label_map)
    def tag(u, s=s):
        if u in s['train_users']: return 'train'
        if u in s['test_users']: return 'test'
        return 'unused'
    feat_exp['split'] = feat_exp.user_id.map(tag)
    feat_exp['label'] = feat_exp.user_id.map(lambda u: label_map.get(u, -1))
    out_path = OUT_DIR / f'coordination_features_exp{exp}.csv'
    feat_exp.to_csv(out_path, index=False)
    n_tr = (feat_exp.split == 'train').sum()
    n_te = (feat_exp.split == 'test').sum()
    print(f'Exp {exp}: {out_path.name}  total={len(feat_exp)}  train={n_tr}  test={n_te}')

print('\n=== Cell 9: Leakage sanity check ===')
rng = np.random.default_rng(RANDOM_SEED)
exp_id = 1
s = splits[exp_id]
feat_real = compute_label_dependent(feat, s, label_map)
all_lbl_users = list(s['train_users'] | s['test_users'])
true_vec = np.array([label_map[u] for u in all_lbl_users])
shuf_vec = rng.permutation(true_vec)
shuf_map = {u: int(l) for u, l in zip(all_lbl_users, shuf_vec)}
feat_shuf = compute_label_dependent(feat, s, {**label_map, **shuf_map})

def auc_on_test(df, lbl_map):
    test_df = df[df.user_id.isin(s['test_users'])].copy()
    test_df['y'] = test_df.user_id.map(lbl_map)
    if test_df.y.nunique() < 2 or test_df.neighbor_sockpuppet_ratio.nunique() < 2:
        return float('nan')
    return roc_auc_score(test_df.y, test_df.neighbor_sockpuppet_ratio)

auc_real = auc_on_test(feat_real, label_map)
auc_shuf = auc_on_test(feat_shuf, {**label_map, **shuf_map})
print(f'AUC real labels:     {auc_real:.3f}')
print(f'AUC shuffled labels: {auc_shuf:.3f}')

print('\n=== Cell 10: Subgroup tagging ===')
sock_group_members = {f'sock_{gid}': set(members) for gid, members in enumerate(sock_groups_master)}
user_threads = {uid: {t for t, _ in acts} for uid, acts in user_activity.items()}
rows = []
for uid, gid in user_to_group.items():
    if not gid.startswith('sock_'):
        continue
    peers = sock_group_members[gid] - {uid}
    my_threads = user_threads.get(uid, set())
    if not peers:
        sub = 'isolated'
    elif any(my_threads & user_threads.get(p, set()) for p in peers):
        sub = 'within_thread'
    else:
        sub = 'cross_thread_only'
    rows.append({'user_id': uid, 'ip_group': gid, 'subgroup': sub,
                 'group_size': len(sock_group_members[gid])})
sub_df = pd.DataFrame(rows)
print(sub_df.subgroup.value_counts())
print()
for exp in (1, 2, 3):
    test_sock = splits[exp]['test_sock']
    seg = sub_df[sub_df.user_id.isin(test_sock)].subgroup.value_counts().to_dict()
    print(f'Exp {exp} test sockpuppets ({len(test_sock)}): {seg}')

print('\n✓ Smoke test passed')
