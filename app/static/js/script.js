const proxyURL = 'https://cors-anywhere.herokuapp.com/';

let fetchHeaders = {
    headers:{
        'Content-Type': 'application/json;charset=utf-8',
        "Access-Control-Allow-Origin" : "*", 
        "Access-Control-Allow-Credentials" : true 
    }
}


async function getGwPicksUser(teamid, gw){
    let entryUrl = "https://fantasy.premierleague.com/api/entry/" + teamid + "/event/" + gw +"/picks/";
    console.log(proxyURL + entryUrl);
    return await fetch(entryUrl)
        .then(function(response) { console.log(response); return response.json();})
        .catch(err => console.log('Request Failed', err));
}

async function getLiveData(gw){
    let liveurl = "https://fantasy.premierleague.com/api/event/" + gw + "/live/";
    return await fetch(liveurl)
        .then(response => response.json())
}

function mapPlayersStats(players, stats){

    let retArr = [];
    for(p in players){
        let d = players[p];
        let pstat = stats[d['element']];
        d['bps'] = pstat['bps'];
        d['minutes'] = pstat['minutes'];
        d['points'] = pstat['total_points'];
        d['bonus'] = pstat['bonus'];
        retArr.push(d);
    }
    return retArr;
}

async function showSquadDetails(teamid, gw){
    console.log(teamid);
    console.log(gw);
    // let userPicks = await getGwPicksUser(teamid, gw);
    // let players_ = await getLiveData(gw);
    
    
    let players = players_['elements'];
    console.log(players);
    
    let playersMap = {}
    for(p in players){
        playersMap[players[p]['id']] = playes[i]['stats'];
    }

    let playerStats = mapPlayersStats(userPicks['picks'], playersMap);
    console.log(playerStats);

}