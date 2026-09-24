const fs=require('fs');
const code=fs.readFileSync('logika.js','utf8');
const STORE={};
function run(event, rows){
  const $=(name)=>{
    if(name==='Читаем календарь') return {all:()=>rows.map(j=>({json:j})), isExecuted:true};
    if(name==='Telegram Trigger') return {isExecuted:!!event, first:()=>({json:event})};
  };
  const f=new Function('$','$getWorkflowStaticData', code);
  return f($,()=>STORE)[0].json;
}
const rows=[{id:'s09',year:'',month:'10',day:'22',title:'День рождения Листа (1811)',channel:'pengui',status:'Идея',sources:'Claude'},
 {id:'s10',year:'',month:'10',day:'31',title:'Halloween',channel:'pengui',status:'Выбран',sources:'Claude; GPT'},{}];
const msg=(text,extra={})=>({message:{chat:{id:1},text,...extra}});
let r=run(msg(`1. 22 октября — День рождения Ференца Листа
- 31.10 Halloween
* October 4 — World Animal Day
Просто текст без даты
20 января 2027: Penguin Awareness Day
20 января — Penguin Awareness Day`),rows);
console.log(r.messages[0].type, r.messages[0].importId); console.log(r.messages[0].text);
const id=r.messages[0].importId;
const cb=(data)=>({callback_query:{id:'q',data,message:{chat:{id:1},message_id:5}}});
r=run(cb(`imp|${id}|src|GPT`),rows); console.log('--src', r.messages.map(m=>m.type));
r=run(cb(`imp|${id}|go`),rows); console.log('--go', JSON.stringify(r.upserts,null,0)); console.log(r.messages[0].text);
r=run(msg('октябрь'),rows); console.log('--month', r.messages.length, r.messages[1].text);
r=run(cb('st|s09|p'),rows); console.log('--st', r.upserts[0].status, r.messages[0].type);
r=run(msg('заметка про Листа',{reply_to_message:{text:'...\nid:s09'}}),rows); console.log('--note', r.upserts[0].note);
r=run(msg('ближайшие'),rows); console.log('--soon\n'+r.messages[0].text);
r=run(null,rows); console.log('--weekly\n'+r.messages[0].text);
r=run(msg('/start'),rows); console.log('--help', r.messages[0].text.slice(0,40));
r=run(msg('май 2027'),rows); console.log('--may', r.messages[0].text);
