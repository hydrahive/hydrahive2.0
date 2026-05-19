export interface CharTemplate {
  name: string
  palette: Record<string, string>
  pixels: string[]
}

export const CHARACTERS: CharTemplate[] = [
  { name: "Steve", palette: { h: "#3b2210", s: "#b58d6a", S: "#8c6a4f", w: "#ffffff", p: "#2b1f7a", m: "#694433", t: "#00a8a8", T: "#008383", d: "#2b2b7a", D: "#1e1e5a", g: "#575757" },
    pixels: ["_hhhhhhhh_","_hhhhhhhh_","_hssssshh_","_ssssssss_","_swpsspws_","_ssssssss_","_ssmmmmss_","_ssssssss_","tTttttttTt","tTttttttTt","tTTTTTTTTt","sTttttttTs","sTttttttTs","sTttttttTs","_sttttttts_","__dddddd__","_dddDDddd_","_dddDDddd_","_ddd__ddd_","_ggg__ggg_"] },
  { name: "Alex", palette: { h: "#c47428", H: "#6e3f14", s: "#b58d6a", S: "#8c6a4f", w: "#ffffff", p: "#3a7a27", m: "#694433", t: "#3c7220", T: "#5d9833", d: "#5c3a1e", D: "#3d2510", g: "#575757" },
    pixels: ["_hHhhhHhh_","_hhhhhhhh_","_hsssssHh_","_ssssssss_","_swpsspws_","_ssssssss_","_ssmmmmss_","_hssssshh_","sTTtttTTTs","sTTtttTTTs","sTTTTTTTTs","sTTtttTTs_","_TtttttT__","_TtttttT__","__tttttt__","__dddddd__","_dddDDddd_","_dddDDddd_","_ddd__ddd_","_ggg__ggg_"] },
  { name: "Zombie", palette: { h: "#3c6620", s: "#5a8832", S: "#486e28", e: "#0c0c0c", m: "#2a4c18", t: "#008383", T: "#006666", d: "#2b2b6e", D: "#1e1e5a", g: "#474747" },
    pixels: ["_hhhhhhhh_","_hhhhhhhh_","_hssssshh_","_ssssssss_","_seeSseeS_","_ssssssss_","_sSmmmmsS_","_ssssssss_","sTttTtttTs","sTttTtttTs","sTTTTTTTTs","sTttTtttTs","sTt_ttttTs","sT__ttttTs","__tttttt__","__dddddd__","_dddDDddd_","_dddDDddd_","_ddd__ddd_","_ggg__ggg_"] },
  { name: "Skeleton", palette: { b: "#c8c8c8", B: "#d4d4d4", d: "#a0a0a0", e: "#1a1a1a", m: "#3a3a3a", g: "#888888" },
    pixels: ["_bbbbbbbb_","_bBbBBbBb_","_bbbbbbbb_","_bBbbbbBb_","_beebbeeb_","_bbbeebbB_","_bmmmmmBb_","_bBbBBbBb_","__dbbBbd__","__dbbBbd__","__dbbbbd__","__dbbBbd__","__dbbbbd__","__dbbBbd__","__dbbbbd__","__dBddBd__","__db__bd__","__db__bd__","__db__bd__","__dg__gd__"] },
  { name: "Creeper", palette: { l: "#5da03a", m: "#4a8c2e", d: "#3a7222", e: "#0c0c0c", D: "#2a5c18" },
    pixels: ["_mlmllmml_","_lmmlmmlm_","_lleellel_","_lleellel_","_llleelll_","_leeeeeml_","_lelllelm_","_mlmlmldm_","__mllllm__","__mllllm__","__mlmmld__","__mllllm__","__mllllm__","__mlmmld__","__mllllm__","_mmm_mmm__","_mDm_mDm__","_mDm_mDm__","_mmm_mmm__","_DDm_mDD__"] },
  { name: "Enderman", palette: { b: "#161616", B: "#1a1a1a", p: "#e079fa", P: "#ff7eff" },
    pixels: ["_bbBbbBbb_","_bBbbbbBb_","_bbbbbbbb_","_bbbbbbbb_","_bppbbppb_","_bbbbbbbb_","_bbbbbbbb_","_bBbbbbBb_","BbbbbbbbBb","Bbb_bb_bBb","_bb_bb_bb_","_bb_bb_bb_","_bbbbbbbb_","_bb_bb_bb_","__b_bb_b__","__bbbbbb__","__b_bb_b__","__b___b___","__b___b___","__b___b___"] },
  { name: "Villager", palette: { s: "#b58d6a", S: "#8c6a4f", n: "#7a5a40", e: "#2b6e2b", b: "#4a3a20", r: "#7a5c3a", R: "#5c4028", g: "#4a3a20" },
    pixels: ["_ssssssss_","_ssssssss_","_sbbbsbbs_","_seessees_","_sssnnsss_","_sssnnsss_","_ssssssss_","_ssssssss_","rRrrrrrrRr","rRrrrrrrRr","rRRRRRRRRr","SRrrrrrrRS","SRrrrrrrRS","SRrrrrrrRS","__rrrrrr__","__rrRRrr__","__rr__rr__","__rr__rr__","__rr__rr__","__gg__gg__"] },
  { name: "Witch", palette: { p: "#3a1d5c", P: "#4a2874", g: "#2ca82c", s: "#b58d6a", S: "#8c6a4f", e: "#7a2b7a", n: "#8c6a4f", w: "#5a8832", r: "#4a2874", R: "#36205a" },
    pixels: ["____pp____","___pppp___","__pppppp__","_pgggggp__","_ssssssss_","_seesseep_","_sssnnsss_","_ssswssss_","rRrrrrrrRr","rRrPPPrrRr","rRRPPPRRRr","sRrPPPrrRs","sRrrrrrrRs","sRrrrrrrRs","__rrrrrr__","__rrRRrr__","__rr__rr__","__rr__rr__","__rr__rr__","__RR__RR__"] },
  { name: "Iron Golem", palette: { s: "#c4b8a8", S: "#a89888", d: "#8c7c6c", e: "#7a2020", v: "#6c8c3c", g: "#575757" },
    pixels: ["_ssssssss_","_sSsSSsSs_","_ssssssss_","_ssssssss_","_seessees_","_ssSddSss_","_ssssssss_","_sSsSSsSs_","dSssssssSD","dSssvsssSD","dSSSvSSSSD","dSssssssSD","dSssssssSD","dSssssssSD","dSssssssSD","__sSddSs__","__sd__ds__","__sd__ds__","__sd__ds__","__gg__gg__"] },
  { name: "Blaze", palette: { y: "#e8b830", Y: "#cc8820", o: "#a86818", e: "#f0e840", r: "#e8c830", k: "#4a4a4a" },
    pixels: ["_yYyyyYyy_","_yYyyyyYy_","_yyyyyyYy_","_yyyyyyyy_","_yeeyYeey_","_yyyyyyyy_","_yoYYYoyy_","_yYyyyyYy_","r_yYYYy_r_","r__yyyy__r","r__yYYy__r","___yyyy___","r__yYYy__r","r________r","____kk____","___kkkk___","____kk____","___kkkk___","____kk____","__________"] },
  { name: "Wither", palette: { b: "#3a3a3a", B: "#4a4a4a", d: "#2a2a2a", e: "#1a1a1a", g: "#333333" },
    pixels: ["_bbBbbBbb_","_bBbBBbBb_","_bbbbbbbb_","_bBbbbbBb_","_beeBbeeb_","_bbbeebbB_","_bdddddBb_","_bBbBBbBb_","__dbbBbd__","__dbbBbd__","__dbbbbd__","__dbbBbd__","__dbbbbd__","__dbbBbd__","__dbbbbd__","__dBddBd__","__db__bd__","__db__bd__","__db__bd__","__dg__gd__"] },
  { name: "Pillager", palette: { h: "#2a2a2a", s: "#7a8a7a", S: "#5c6c5c", e: "#1a1a1a", b: "#3a3a3a", t: "#3a3a4a", T: "#2a2a3a", l: "#6a5a3a", g: "#4a3a20" },
    pixels: ["_hhhhhhhh_","_hhhhhhhh_","_hssssssh_","_sbbbsbbs_","_seeSseeb_","_ssssssss_","_sSSSSSsS_","_ssssssss_","tTttttttTt","tTttllttTt","tTTlllTTTt","sTttllttTs","sTttttttTs","sTttttttTs","__tttttt__","__ttTTtt__","__tt__tt__","__tt__tt__","__tt__tt__","__gg__gg__"] },
]

export function getCharForAgent(name: string): CharTemplate {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0
  return CHARACTERS[Math.abs(hash) % CHARACTERS.length]
}
