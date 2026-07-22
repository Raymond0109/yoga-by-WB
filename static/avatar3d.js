/**
 * 3D Avatar Module for Yoga Flow UI
 * Exposes window.Avatar3D API compatible with existing index.html
 */

// POSE_CONNECTIONS defined in main HTML
const POSE_CONNECTIONS = window.POSE_CONNECTIONS || [
  [0,1],[1,2],[2,3],[3,7], [0,4],[4,5],[5,6],[6,8], [9,10],
  [11,12],[11,13],[13,15],[12,14],[14,16],
  [11,23],[12,24],[23,24],[23,25],[25,27],[24,26],[26,28]
];

let renderer, scene, camera, skel, ghost, muscleGroup;
let _chkM, _chkG;
let MUSCLE_UNITS3D = [];

const MIRROR3D = {11:12,12:11,13:14,14:13,15:16,16:15,23:24,24:23,25:26,26:25,27:28,28:27};

const V3 = {
  sub:(a,b)=>({x:a.x-b.x, y:a.y-b.y, z:a.z-b.z}),
  len:(v)=>Math.hypot(v.x,v.y,v.z)||1,
  norm:(v)=>{ const l=Math.hypot(v.x,v.y,v.z)||1; return {x:v.x/l, y:v.y/l, z:v.z/l}; },
  dot:(a,b)=>a.x*b.x+a.y*b.y+a.z*b.z,
  lerp:(a,b,t)=>({x:a.x+(b.x-a.x)*t, y:a.y+(b.y-a.y)*t, z:a.z+(b.z-a.z)*t}),
  dist:(a,b)=>Math.hypot(a.x-b.x, a.y-b.y, a.z-b.z),
  three:(p)=>({x:p.x, y:-p.y, z:-p.z}),
};

const STRETCH_RANGE = 60;
const STRETCH_CFG = {
  deltoid:   {joint:[11,12,14], dir:+1, neutral:90},
  biceps:    {joint:[12,14,16], dir:+1, neutral:175},
  triceps:   {joint:[12,14,16], dir:-1, neutral:175},
  forearm:   {joint:[12,14,16], dir:+1, neutral:175},
  obliques:  {joint:[11,12,24], dir:+1, neutral:120},
  glutes:    {joint:[12,24,26], dir:-1, neutral:170},
  quads:     {joint:[24,26,28], dir:-1, neutral:175},
  hamstrings:{joint:[24,26,28], dir:+1, neutral:175},
  calves:    {joint:[24,26,28], dir:+1, neutral:175},
  pectoral:  {joint:[11,12,14], dir:+1, neutral:90},
  rectus:    {joint:[11,23,24], dir:+1, neutral:90},
  traps:     {joint:[11,12,14], dir:+1, neutral:90},
  spinal:    {joint:[11,23,24], dir:+1, neutral:90},
};

const ID_MAP3D = {
  hamstrings: ['hamstrings'], deltoids: ['deltoid', 'traps'], triceps: ['triceps'],
  biceps: ['biceps'], spinal: ['spinal'], calves: ['calves'], quads_stand: ['quads'],
  quads: ['quads'], quads_front: ['quads'], hip_flexors: ['quads'], glutes: ['glutes'],
  glutes_back: ['glutes'], obliques: ['obliques'], core: ['rectus', 'obliques'], rectus: ['rectus'],
  pectorals: ['pectoral'], pectoral: ['pectoral'], pecs: ['pectoral'], chest: ['pectoral'], trapezius: ['traps'], traps: ['traps'],
  forearms: ['forearm'], forearm: ['forearm'],
};

const MUSCLE_MAP3D = [
  {id:'deltoid', seg:[12,14], side:'both', face:'outer', width:0.26},
  {id:'biceps', seg:[12,14], side:'both', face:'front', width:0.18},
  {id:'triceps', seg:[12,14], side:'both', face:'back', width:0.18},
  {id:'forearm', seg:[14,16], side:'both', face:'front', width:0.15},
  {id:'obliques', seg:[12,24], side:'both', face:'outer', width:0.18},
  {id:'glutes', seg:[24,26], side:'both', face:'back', width:0.28},
  {id:'quads', seg:[24,26], side:'both', face:'front', width:0.20},
  {id:'hamstrings', seg:[24,26], side:'both', face:'back', width:0.18},
  {id:'calves', seg:[26,28], side:'both', face:'back', width:0.18},
];

function angleDeg(world, a, b, c) {
  const A = world[a], B = world[b], C = world[c];
  if (!A || !B || !C) return null;
  const v1x=A.x-B.x, v1y=A.y-B.y, v1z=A.z-B.z;
  const v2x=C.x-B.x, v2y=C.y-B.y, v2z=C.z-B.z;
  const l1 = Math.hypot(v1x,v1y,v1z)||1e-6, l2 = Math.hypot(v2x,v2y,v2z)||1e-6;
  let cos = (v1x*v2x+v1y*v2y+v1z*v2z)/(l1*l2);
  return Math.acos(Math.max(-1, Math.min(1, cos))) * 180 / Math.PI;
}

function mirrorJoint(j) { return j.map(i => MIRROR3D[i] != null ? MIRROR3D[i] : i); }

function stretchOf(id, world) {
  const cfg = STRETCH_CFG[id];
  if (!cfg) return 0.5;
  const j = cfg.joint;
  const ang = angleDeg(world, j[0], j[1], j[2]);
  if (ang == null) return 0.5;
  return 0.5 - 0.5 * Math.max(-1, Math.min(1, cfg.dir * (ang - cfg.neutral) / STRETCH_RANGE));
}

function heatRGB3(l) {
  l = Math.max(0, Math.min(1, l));
  let c;
  if (l < 0.5) { const t = l/0.5; c = [59+(245-59)*t, 130+(158-130)*t, 246+(11-246)*t]; }
  else { const t = (l-0.5)/0.5; c = [245+(239-245)*t, 158+(68-158)*t, 11+(68-11)*t]; }
  return [c[0]|0, c[1]|0, c[2]|0];
}

function frontDirWorld(world) {
  const hip = V3.lerp(world[23], world[24], 0.5);
  const nose = world[0];
  if (!hip || !nose || nose.v < 0.3) return {x:0, y:0, z:1};
  return V3.norm(V3.sub(nose, hip));
}

function centerDirWorld(world) {
  const sh = V3.lerp(world[11], world[12], 0.5);
  const hip = V3.lerp(world[23], world[24], 0.5);
  return V3.lerp(sh, hip, 0.5);
}

function makeSkeleton(color, opacity, opts={}) {
  const { joints: withJoints=true, jointRadius=0.022 } = opts;
  const g = new THREE.Group();
  const joints = [];
  if (withJoints) {
    const jointGeo = new THREE.SphereGeometry(jointRadius, 12, 12);
    const jointMat = new THREE.MeshStandardMaterial({ color, transparent: opacity < 1, opacity });
    for (let i = 0; i < 33; i++) {
      const m = new THREE.Mesh(jointGeo, jointMat);
      g.add(m); joints.push(m);
    }
  }
  const linePos = new Float32Array(POSE_CONNECTIONS.length * 2 * 3);
  const lineGeo = new THREE.BufferGeometry();
  lineGeo.setAttribute('position', new THREE.BufferAttribute(linePos, 3));
  const lineMat = new THREE.LineBasicMaterial({ color, transparent: opacity < 1, opacity });
  const lines = new THREE.LineSegments(lineGeo, lineMat);
  g.add(lines);
  g.userData = { joints, lineGeo, linePos };
  return g;
}

function setSkeleton(grp, world) {
  const { joints, lineGeo, linePos } = grp.userData;
  if (!world || world.length < 33) return;
  for (let i = 0; i < 33; i++) {
    const p = world[i];
    if (joints[i]) joints[i].position.set(p.x, -p.y, -p.z);
  }
  let k = 0;
  for (const c of POSE_CONNECTIONS) {
    const a = world[c[0]], b = world[c[1]];
    linePos[k++] = a.x; linePos[k++] = -a.y; linePos[k++] = -a.z;
    linePos[k++] = b.x; linePos[k++] = -b.y; linePos[k++] = -b.z;
  }
  lineGeo.attributes.position.needsUpdate = true;
}

// Initialize 3D scene
function init3D(canvasId) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;

  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(50, 1, 0.01, 100);
  camera.position.set(0, -0.2, 2.4);

  scene.add(new THREE.AmbientLight(0xffffff, 0.75));
  const dl = new THREE.DirectionalLight(0xffffff, 0.9);
  dl.position.set(1, 1, 2);
  scene.add(dl);

  skel = makeSkeleton(0xe8e8e8, 0.95);
  ghost = makeSkeleton(0xffa657, 0.15, { joints: false });
  ghost.visible = false;
  scene.add(skel);
  scene.add(ghost);

  // Muscles (simplified for now)
  muscleGroup = new THREE.Group();
  scene.add(muscleGroup);

  _chkM = document.getElementById('chkMuscles3d');
  _chkG = document.getElementById('chkGhost3d');

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.target.set(0, 0, 0);

  function resize() {
    const w = canvas.clientWidth || 360, h = canvas.clientHeight || 480;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  resize();
  animate();

  // Expose API
  window.Avatar3D = {
    update(world, feedback) {
      setSkeleton(skel, world);
    },
    setGhost(world) {
      if (world && world.length >= 33) {
        setSkeleton(ghost, world);
        ghost.visible = !!(_chkG && _chkG.checked);
      } else {
        ghost.visible = false;
      }
    },
    clearGhost() { ghost.visible = false; },
    getGhostState() { return { visible: ghost.visible, asana: window.__ghostAsanaId || null, hasData: !!ghost.userData.lineGeo }; },
    toggleMuscles(on) { muscleGroup.visible = on; },
    getMuscleState() { return []; }
  };
}

// Export
window.init3D = init3D;
