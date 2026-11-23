from __future__ import annotations

import heapq
import json
import math

GRID = .25


def _wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def _turn_actions(delta, vertical=False):
    degrees = int(round(math.degrees(delta) / 10)) * 10
    direction = ('up' if degrees > 0 else 'down') if vertical else ('left' if degrees > 0 else 'right')
    remaining = abs(degrees)
    actions = []
    while remaining:
        amount = min(120, remaining)
        actions.append(dict(action='turn', direction=direction, degrees=amount))
        remaining -= amount
    return actions


def _edge_clear(a, b, blocked):
    n = max(1, math.ceil(math.dist(a, b) / .04))
    for i in range(1, n + 1):
        f = i / n
        if blocked(a[0] + (b[0]-a[0])*f, a[1] + (b[1]-a[1])*f):
            return False
    return True


def route_nodes(start_xy, dest_xy, blocked, max_nodes=50000):
    if len(start_xy) < 2 or len(dest_xy) < 2 or not all(math.isfinite(float(x)) for x in (*start_xy[:2], *dest_xy[:2])):
        raise ValueError('Finite start/destination XY coordinates required.')
    start = tuple(int(round(float(v)/GRID)) for v in start_xy[:2])
    goal = tuple(int(round(float(v)/GRID)) for v in dest_xy[:2])
    xy = lambda n: (n[0]*GRID, n[1]*GRID)
    if math.dist(xy(start),start_xy[:2]) > .005:
        raise ValueError('Start is not on .25m lattice; do not silently snap real pose.')
    if blocked(*xy(start)):
        raise ValueError('Route start is blocked.')
    if blocked(*xy(goal)):
        raise ValueError('Rounded destination stand point is blocked: %s' % (xy(goal),))
    h = lambda n: abs(n[0]-goal[0])+abs(n[1]-goal[1])
    queue = [(h(start), 0, start)]
    costs, parents = {start:0}, {}
    expanded = 0
    while queue:
        _, cost, node = heapq.heappop(queue)
        if cost != costs[node]:
            continue
        if node == goal:
            path = [node]
            while node != start:
                node = parents[node]
                path.append(node)
            return [xy(n) for n in reversed(path)]
        expanded += 1
        if expanded > max_nodes:
            raise RuntimeError('No route within offline oracle node budget.')
        for dx,dy in ((1,0),(0,1),(-1,0),(0,-1)):
            nxt=(node[0]+dx,node[1]+dy)
            if cost+1 >= costs.get(nxt,math.inf) or not _edge_clear(xy(node),xy(nxt),blocked):
                continue
            costs[nxt]=cost+1
            parents[nxt]=node
            heapq.heappush(queue,(cost+1+h(nxt),cost+1,nxt))
    raise RuntimeError('No collision-free route to stand point.')


def plan_route(start_xy, dest_xy, blocked, yaw=0.0):
    if not math.isfinite(yaw):
        raise ValueError('Finite yaw required.')
    nearest=math.radians(round(math.degrees(yaw)/10)*10)
    if abs(_wrap(yaw-nearest)) > 1e-4:
        raise ValueError('Yaw is not on 10-degree lattice; cannot promise exact cardinal route.')
    nodes=route_nodes(start_xy,dest_xy,blocked)
    runs=[]
    for a,b in zip(nodes,nodes[1:]):
        direction=(round((b[0]-a[0])/GRID),round((b[1]-a[1])/GRID))
        if runs and runs[-1][0] == direction:
            runs[-1][1]+=1
        else:
            runs.append([direction,1])
    actions=[]
    for (dx,dy),cells in runs:
        heading=math.atan2(dy,dx)
        actions.extend(_turn_actions(_wrap(heading-yaw)))
        yaw=heading
        for size in (4,2,1):
            number,cells=divmod(cells,size)
            actions.extend(dict(action='walk',distance=size*GRID) for _ in range(number))
    return actions


def aim_actions(pos, yaw, pitch, target3d, eye_height=1.35):
    if len(pos) < 2 or len(target3d) != 3:
        raise ValueError('pos needs XY/XYZ and target needs XYZ.')
    x,y=map(float,pos[:2]);z=float(pos[2]) if len(pos)>2 else float(eye_height)
    dx,dy,dz=float(target3d[0])-x,float(target3d[1])-y,float(target3d[2])-z
    if not all(math.isfinite(v) for v in (dx,dy,dz,yaw,pitch)):
        raise ValueError('Finite pose and target required.')
    horizontal=math.hypot(dx,dy)
    desired_yaw=math.atan2(dy,dx) if horizontal>1e-9 else yaw
    desired_pitch=max(-math.pi/3,min(math.pi/3,math.atan2(dz,horizontal)))
    return _turn_actions(_wrap(desired_yaw-yaw)) + _turn_actions(desired_pitch-pitch,vertical=True)


def self_test():
    def blocked(x,y):
        return abs(x)>2 or abs(y)>2 or (abs(x)<.10 and y<.75)
    start,goal=(-1.,0.),(1.,0.)
    actions=plan_route(start,goal,blocked,yaw=math.radians(30))
    p=list(start);yaw=math.radians(30)
    for a in actions:
        if a['action']=='turn':
            assert 10 <= a['degrees'] <= 120 and a['degrees']%10==0
            yaw += math.radians(a['degrees'])*(1 if a['direction']=='left' else -1)
        else:
            assert a['distance'] in (.25,.5,1.)
            nxt=[p[0]+a['distance']*math.cos(yaw),p[1]+a['distance']*math.sin(yaw)]
            assert _edge_clear(p,nxt,blocked)
            p=nxt
    assert math.dist(p,goal)<1e-8
    count=0
    for degrees in range(-180,180,10):
        for desired in range(-175,180,7):
            yaw=math.radians(degrees);pitch=0.
            t=[math.cos(math.radians(desired)),math.sin(math.radians(desired)),1.55]
            for a in aim_actions([0,0,1.35],yaw,pitch,t):
                delta=math.radians(a['degrees'])
                if a['direction'] in ('left','right'):yaw+=delta*(1 if a['direction']=='left' else -1)
                else:pitch+=delta*(1 if a['direction']=='up' else -1)
            assert abs(_wrap(yaw-math.radians(desired)))<=math.radians(5.00001)
            assert abs(pitch-math.atan2(.2,1.))<=math.radians(5.00001)
            count+=1
    print(json.dumps(dict(passed=True,route_actions=len(actions),route_final=p,aim_cases=count,
                         paid_calls=0,sdk_loaded=False,scope='offline CPU planner, not native route execution')))


if __name__=='__main__':
    self_test()
