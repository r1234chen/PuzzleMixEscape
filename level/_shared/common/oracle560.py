import heapq,math
from oracle355 import _edge_clear,_turn_actions,_wrap,GRID
def plan_route(start_xy,dest_xy,blocked,yaw=0.):
 start=tuple(round(float(x)/GRID) for x in start_xy[:2]);goal=tuple(round(float(x)/GRID) for x in dest_xy[:2]);xy=lambda n:(n[0]*GRID,n[1]*GRID)
 if math.dist(xy(start),start_xy[:2])>.005:raise ValueError('Non-lattice start, no snapping allowed')
 if blocked(*xy(start)) or blocked(*xy(goal)):raise ValueError('Blocked route endpoint')
 if start==goal:return []
 queue=[(0,0.,start)];cost={start:(0,0.)};parent={}
 while queue:
  count,length,n=heapq.heappop(queue)
  if cost[n]!=(count,length):continue
  if n==goal:break
  for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
   for step in (4,2,1):
    nn=(n[0]+dx*step,n[1]+dy*step);v=(count+1,length+step*GRID)
    if v>=cost.get(nn,(math.inf,math.inf)) or not _edge_clear(xy(n),xy(nn),blocked):continue
    cost[nn]=v;parent[nn]=(n,(dx,dy),step);heapq.heappush(queue,(v[0],v[1],nn))
 else:raise RuntimeError('No swept-clear path')
 edges=[];n=goal
 while n!=start:
  n0,heading,step=parent[n];edges.append((heading,step));n=n0
 edges.reverse()
 options=[]
 for k in range(4):
  heading=k*math.pi/2;turns=_turn_actions(_wrap(heading-yaw));options.append((len(turns),abs(_wrap(heading-yaw)),k,turns))
 _,_,k,actions=min(options);actions=list(actions)
 for (dx,dy),step in edges:
  direction=(round(math.atan2(dy,dx)/(math.pi/2))-k)%4
  action={'action':('walk' if direction==0 else 'step_back' if direction==2 else 'side_step'),'distance':step*GRID}
  if direction in (1,3):action['direction']='left' if direction==1 else 'right'
  actions.append(action)
 return actions
