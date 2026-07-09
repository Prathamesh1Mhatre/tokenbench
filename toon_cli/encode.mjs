import { encode } from "@toon-format/toon";
let s=""; process.stdin.on("data",d=>s+=d).on("end",()=>{
  try { process.stdout.write(encode(JSON.parse(s))); } catch(e){ process.stdout.write(s); }
});
