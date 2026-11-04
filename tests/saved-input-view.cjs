const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(process.argv[2]||require('path').join(__dirname,'../index.html'),'utf8');
const script=[...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map(x=>x[1]).join('\n').replace(/\nreconnectApp\(\);\s*$/,'');
const el={innerHTML:''},c={console,Date,Number,Math,JSON,Set,Map,URLSearchParams,navigator:{},window:{},localStorage:{getItem:()=>null},document:{getElementById:()=>el}};
vm.createContext(c);vm.runInContext(script,c);
vm.runInContext(`DATA={lineups:[{rank:1,players:['Saved Player'],proj:12.3,salary:5000,playerProjections:[12.3],projectionSource:'saved',ceil:18,ceilingSource:'saved'}],portfolioHealth:{status:'REGENERATE',message:'Inputs changed <check>',generatedAt:'2026-11-04T20:00:00Z'}};renderLineups();`,c);
assert(el.innerHTML.includes('Saved player projections'));assert(el.innerHTML.includes('12.3 projected pts'));assert(el.innerHTML.includes('Inputs changed &lt;check&gt;'));assert(!el.innerHTML.includes('Current player projections'));
console.log('PASS: saved forecasts and escaped portfolio health warning render together.');
