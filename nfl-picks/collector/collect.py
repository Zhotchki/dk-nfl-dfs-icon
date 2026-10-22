"""Collect public NFL board lines; never substitute projections for live lines."""
import concurrent.futures, datetime as dt, json, os, pathlib, urllib.request

ROOT = pathlib.Path(__file__).parent
URLS = {'sleeper':'https://api.sleeper.app/lines/available','underdog':'https://api.underdogfantasy.com/v1/over_under_lines','players':'https://api.sleeper.app/v1/players/nfl'}
MARKETS={'passing_yards':'Pass Yards','passing_yds':'Pass Yards','passing_attempts':'Pass Attempts','pass_completions':'Pass Completions','passing_completions':'Pass Completions','passing_touchdowns':'Pass TDs','passing_tds':'Pass TDs','interceptions':'Interceptions','rushing_yards':'Rush Yards','rushing_yds':'Rush Yards','rushing_attempts':'Rush Attempts','receiving_yards':'Receiving Yards','receiving_yds':'Receiving Yards','receptions':'Receptions','rushing_and_receiving_yards':'Rush + Receiving Yards','rush_rec_yds':'Rush + Receiving Yards','anytime_touchdowns':'Scoring TDs'}
MARKETS.update({'passing_att':'Pass Attempts','passing_comps':'Pass Completions','passing_ints':'Interceptions','rushing_att':'Rush Attempts','receiving_rec':'Receptions','receiving_tgts':'Targets','rush_rec_tds':'Scoring TDs'})

def get(name):
    fixture=os.environ.get('BOARD_FIXTURES')
    if fixture and name!='players': return json.loads(pathlib.Path(fixture,f'free-{name}.json').read_text())
    req=urllib.request.Request(URLS[name],headers={'Accept':'application/json','User-Agent':'NFL-Picks-Personal/1.0'})
    with urllib.request.urlopen(req,timeout=55) as response: return json.load(response)

def sleeper_rows(data,players):
    rows=[]
    if not isinstance(data,list) or not isinstance(players,dict): raise ValueError('Unexpected Sleeper schema')
    for r in data:
        market=MARKETS.get(r.get('wager_type'))
        if r.get('sport')!='nfl' or r.get('status')!='active' or r.get('game_status')!='pre_game' or r.get('line_type')!='normal' or not market: continue
        p=players.get(str(r.get('subject_id')),{});name=p.get('full_name') or ' '.join(filter(None,[p.get('first_name'),p.get('last_name')]))
        if not name: continue
        for o in r.get('options',[]):
            if o.get('status')!='active' or o.get('outcome') not in ['over','under'] or not isinstance(o.get('outcome_value'),(int,float)): continue
            rows.append({'platform':'Sleeper','id':str(o.get('line_id','')),'player':name,'team':o.get('subject_team'),'market':market,'line':o['outcome_value'],'side':'Higher' if o['outcome']=='over' else 'Lower','multiplier':o.get('payout_multiplier'),'gameId':str(r.get('game_id','')),'season':str(r.get('season','')),'updatedAt':r.get('updated_at')})
    return rows

def underdog_rows(data):
    if not isinstance(data,dict) or not isinstance(data.get('over_under_lines'),list): raise ValueError('Unexpected Underdog schema')
    players={str(p['id']):p for p in data['players']};appearances={str(p['id']):p for p in data['appearances']};games={str(p['id']):p for p in data['games']};rows=[]
    for r in data['over_under_lines']:
        st=r.get('over_under',{}).get('appearance_stat',{});market=MARKETS.get(st.get('stat'));a=appearances.get(str(st.get('appearance_id')),{});p=players.get(str(a.get('player_id')),{});g=games.get(str(a.get('match_id')),{});
        if p.get('sport_id')!='NFL' or not market or r.get('status')!='active' or r.get('live_event') or g.get('status')!='scheduled' or r.get('line_type')!='balanced': continue
        teams=g.get('abbreviated_title','').split(' @ ')
        if len(teams)!=2: continue
        home=a.get('team_id')==g.get('home_team_id');team,opp=(teams[1],teams[0]) if home else (teams[0],teams[1])
        try: line=float(r['stat_value'])
        except (ValueError,TypeError,KeyError): continue
        name=' '.join(filter(None,[p.get('first_name'),p.get('last_name')]))
        if not name: continue
        for o in r.get('options',[]):
            if o.get('status')!='active' or o.get('choice') not in ['higher','lower']: continue
            rows.append({'platform':'Underdog','id':str(o.get('id','')),'player':name,'team':team,'opponent':opp,'market':market,'line':line,'side':'Higher' if o['choice']=='higher' else 'Lower','multiplier':o.get('payout_multiplier'),'gameId':str(g['id']),'kickoff':g.get('scheduled_at'),'updatedAt':r.get('updated_at')})
    return rows

def main():
    now=dt.datetime.now(dt.timezone.utc).isoformat();loaded={};errors={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        jobs={pool.submit(get,name):name for name in URLS}
        for future in concurrent.futures.as_completed(jobs):
            name=jobs[future]
            try:loaded[name]=future.result()
            except Exception as e:errors[name]=str(e)
    result={'schema':1,'fetchedAt':now,'sources':{},'lines':[]}
    for platform,parser,args in [('Sleeper',sleeper_rows,['sleeper','players']),('Underdog',underdog_rows,['underdog'])]:
        try:
            if any(x in errors for x in args):raise ValueError('; '.join(errors[x] for x in args if x in errors))
            rows=parser(*(loaded[x] for x in args));result['lines'].extend(rows);result['sources'][platform]={'status':'ok','count':len(rows)}
        except Exception as e:result['sources'][platform]={'status':'unavailable','count':0,'message':str(e)[:160]}
    target=ROOT/'board.json';target.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print(json.dumps({'fetchedAt':now,'sources':result['sources']}))

if __name__=='__main__': main()
