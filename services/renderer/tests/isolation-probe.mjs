// Executes inside the exact renderer sandbox; never imports generated source on host.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import net from 'node:net';
const denied = async (host) => new Promise((resolve,reject)=>{
 const socket=net.connect({host,port:80});
 socket.setTimeout(1500);
 socket.on('connect',()=>{socket.destroy();reject(Error('Unexpected network access'))});
 socket.on('error',()=>resolve(true));
 socket.on('timeout',()=>{socket.destroy();resolve(true)});
});
assert.notEqual(process.getuid(),0);
assert.throws(()=>fs.writeFileSync('/opt/renderer/escape','bad'));
assert.throws(()=>fs.readFileSync('/Users/agastyasandhuja/Documents/hackumass-14/services/api/.env'));
assert.equal(fs.existsSync('/var/run/docker.sock'),false);
for(const name of ['ANTHROPIC_API_KEY','ELEVENLABS_API_KEY','SUPABASE_SERVICE_ROLE_KEY','MONGODB_URI']) assert.equal(process.env[name],undefined);
await denied('1.1.1.1'); await denied('169.254.169.254');
assert.equal(fs.readFileSync('/sys/fs/cgroup/pids.max','utf8').trim(),'256');
assert.equal(fs.readFileSync('/sys/fs/cgroup/memory.max','utf8').trim(),String(4*1024**3));
assert.match(fs.readFileSync('/proc/self/status','utf8'),/NoNewPrivs:\s+1/);
assert.match(fs.readFileSync('/proc/self/status','utf8'),/CapEff:\s+0+/);
console.log(JSON.stringify({non_root:true,read_only_root:true,host_secret_absent:true,credentials_absent:true,egress_blocked:true,metadata_blocked:true,pid_limit:256,memory_gib:4,no_new_privileges:true,capabilities_dropped:true}));
