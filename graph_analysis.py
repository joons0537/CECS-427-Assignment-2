#!/usr/bin/env python3
"""graph_analysis.py - CECS 427 Project
Analyze and visualize graphs: clustering, overlap, communities, homophily,
balance, failures, robustness, and temporal evolution.
"""

import argparse, csv, math, os, random, sys
from collections import deque
from datetime import datetime
import matplotlib.pyplot as plt, networkx as nx, numpy as np

try:
    from scipy.stats import ttest_ind
    SCIPY = True
except:
    SCIPY = False

def eprint(*x): print(*x, file=sys.stderr)

def load_graph(path):
    if not os.path.exists(path): raise FileNotFoundError(path)
    G = nx.read_gml(path)
    if isinstance(G, (nx.DiGraph, nx.MultiDiGraph)):
        UG = nx.Graph()
        [UG.add_edge(u,v,**d) for u,v,d in G.edges(data=True)]
        [UG.add_node(n,**d) for n,d in G.nodes(data=True)]
        G = UG
    if G.number_of_nodes()==0: eprint('[warn] Empty graph')
    return G

def layout(G):
    if 'pos' not in G.graph: G.graph['pos']=nx.spring_layout(G,seed=42)
    return G.graph['pos']

def clustering(G):
    cc=nx.clustering(G); nx.set_node_attributes(G,cc,'cc'); return cc

def overlap(G):
    data={}
    for u,v in G.edges():
        Nu,Nv=set(G.neighbors(u))- {v}, set(G.neighbors(v))- {u}
        d=len(Nu|Nv)
        data[(u,v)]=0 if d==0 else len(Nu&Nv)/d
    nx.set_edge_attributes(G,{tuple(sorted([u,v])):{'no':data[(u,v)]} for u,v in G.edges()})
    return data

def girvan_newman_partition(G,n):
    from networkx.algorithms.community import girvan_newman
    comp=nx.connected_components(G) if G.number_of_edges()==0 else next(girvan_newman(G))
    try:
        gen=girvan_newman(G)
        for _ in range(n-1): comp=next(gen)
    except: pass
    return [sorted(list(c)) for c in comp]

def annotate(G,parts):
    d={n:i for i,p in enumerate(parts) for n in p}
    nx.set_node_attributes(G,d,'community')

def homophily(G):
    same,diff=[],[]
    for u,v in G.edges():
        cu,cv=G.nodes[u].get('color'),G.nodes[v].get('color')
        if cu is None or cv is None: continue
        sim=-abs(G.degree(u)-G.degree(v))
        (same if cu==cv else diff).append(sim)
    if len(same)<2 or len(diff)<2: return {'error':'not enough data'}
    if SCIPY: t,p=ttest_ind(same,diff,equal_var=False)
    else:
        m1,m2=np.mean(same),np.mean(diff)
        s1,s2=np.var(same,ddof=1),np.var(diff,ddof=1)
        t=(m1-m2)/math.sqrt(s1/len(same)+s2/len(diff))
        p=0.05
    d=(np.mean(same)-np.mean(diff))/max(1e-9,math.sqrt(((len(same)-1)*np.var(same,ddof=1)+(len(diff)-1)*np.var(diff,ddof=1))/(len(same)+len(diff)-2)))
    return {'t':round(t,3),'p':round(p,4),'d':round(d,3)}

def balance(G):
    label={}
    for s in G.nodes():
        if s in label: continue
        label[s]=1; q=deque([s])
        while q:
            u=q.popleft()
            for v in G.neighbors(u):
                sign=int(G[u][v].get('sign',1))
                exp=label[u]* (1 if sign>=0 else -1)
                if v not in label: label[v]=exp; q.append(v)
                elif label[v]!=exp: return False
    return True

def stats(G):
    comps=[G.subgraph(c).copy() for c in nx.connected_components(G)]
    if not comps: return {'aspl':None,'n':0,'sizes':[]}
    LCC=max(comps,key=lambda H:H.number_of_nodes())
    asp=nx.average_shortest_path_length(LCC) if LCC.number_of_edges()>0 else None
    return {'aspl':asp,'n':len(comps),'sizes':[len(c) for c in comps]}

def simulate_failures(G,k):
    before=stats(G)
    H=G.copy(); edges=list(G.edges()); rem=random.sample(edges,min(k,len(edges)))
    H.remove_edges_from(rem); after=stats(H)
    return before,after

def robustness(G,k,trials,parts=None):
    res=[]
    for _ in range(trials):
        H=G.copy(); H.remove_edges_from(random.sample(list(H.edges()),min(k,H.number_of_edges())))
        s=stats(H); res.append(s['n'])
    return {'avg_comp':np.mean(res) if res else 0}

def plot_graph(G,mode,out=None):
    pos=layout(G); plt.figure(figsize=(8,6))
    if mode=='C':
        clustering(G); c=[G.degree(n) for n in G]
        s=[300+2000*G.nodes[n].get('cc',0) for n in G]
        nx.draw(G,pos,node_size=s,node_color=c,cmap=plt.cm.viridis,with_labels=True)
    elif mode=='N':
        overlap(G); w=[1+6*G[u][v]['no'] for u,v in G.edges()]
        nx.draw(G,pos,with_labels=True,width=w,edge_color='gray')
    elif mode=='P':
        ncol=[G.nodes[n].get('color','gray') for n in G]
        ecol=['green' if int(G[u][v].get('sign',1))>=0 else 'red' for u,v in G.edges()]
        nx.draw(G,pos,with_labels=True,node_color=ncol,edge_color=ecol)
    else: nx.draw(G,pos,with_labels=True)
    if out: plt.savefig(out,dpi=200); eprint(f'saved {out}')
    else: plt.show(); plt.close()

def export_graph(G,out):
    H=G.copy(); H.graph.pop('pos',None)
    nx.write_gml(H,out)

def parse_csv(path):
    ev=[]
    with open(path) as f:
        for r in csv.DictReader(f):
            t=datetime.fromisoformat(r['timestamp']).timestamp()
            ev.append((t,r['source'],r['target'],r['action'].lower()))
    return sorted(ev)

def temporal(G,path,out=None):
    ev=parse_csv(path); pos=layout(G); snaps=[]
    for _,u,v,a in ev:
        if a=='add': G.add_edge(u,v)
        elif a=='remove' and G.has_edge(u,v): G.remove_edge(u,v)
        snaps.append(G.copy())
    if out:
        import matplotlib.animation as animation
        fig=plt.figure(figsize=(8,6))
        def upd(i): plt.clf(); nx.draw(snaps[i],pos,node_size=100,width=0.8)
        ani=animation.FuncAnimation(fig,upd,frames=len(snaps),interval=500)
        ani.save(out,writer='pillow',dpi=120); eprint(f'GIF saved {out}')
    return len(ev)

def main():
    p=argparse.ArgumentParser();
    p.add_argument('graph');
    p.add_argument('--components',type=int); p.add_argument('--plot'); p.add_argument('--plot_out');
    p.add_argument('--verify_homophily',action='store_true'); p.add_argument('--verify_balanced_graph',action='store_true');
    p.add_argument('--simulate_failures',type=int); p.add_argument('--robustness_check',type=int); p.add_argument('--robustness_trials',type=int,default=30);
    p.add_argument('--temporal_simulation'); p.add_argument('--temporal_gif'); p.add_argument('--output');
    a=p.parse_args()

    G=load_graph(a.graph); eprint(f'Loaded {G.number_of_nodes()} nodes, {G.number_of_edges()} edges')
    clustering(G); overlap(G)

    if a.components: parts=girvan_newman_partition(G,a.components); annotate(G,parts); eprint(f'Communities: {len(parts)}')
    if a.plot: plot_graph(G,a.plot,a.plot_out)
    if a.verify_homophily: eprint('Homophily:',homophily(G))
    if a.verify_balanced_graph: eprint('Balanced:' if balance(G) else 'Not balanced')
    if a.simulate_failures is not None:
        b,aft=simulate_failures(G,a.simulate_failures); eprint(f'Before:{b} After:{aft}')
    if a.robustness_check: eprint('Robustness:',robustness(G,a.robustness_check,a.robustness_trials))
    if a.temporal_simulation: eprint(f'Temporal events:{temporal(G,a.temporal_simulation,a.temporal_gif)}')
    if a.output: export_graph(G,a.output); eprint(f'Saved graph to {a.output}')

if __name__=='__main__': main()