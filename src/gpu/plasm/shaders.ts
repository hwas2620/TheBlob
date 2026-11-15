// 원형질체 코어의 셰이더 소스 — .glsl 을 불러와 플레이스홀더를 치환한다

import { resolveShader } from '../shaderUtils';
import mgJacobi from './shaders/mg_jacobi.frag.glsl?raw';
import mgResidual from './shaders/mg_residual.frag.glsl?raw';
import mgRestrict from './shaders/mg_restrict.frag.glsl?raw';
import mgProlong from './shaders/mg_prolong.frag.glsl?raw';
import mgCoarsen from './shaders/mg_coarsen.frag.glsl?raw';
import edgeActivate from './shaders/edge_activate.frag.glsl?raw';
import phase from './shaders/phase.frag.glsl?raw';
import rest from './shaders/rest.frag.glsl?raw';
import mgInit from './shaders/mg_init.frag.glsl?raw';
import flux from './shaders/flux.frag.glsl?raw';
import reduceQ0 from './shaders/reduce_q0.frag.glsl?raw';
import reduceSum from './shaders/reduce_sum.frag.glsl?raw';
import reduceStats from './shaders/reduce_stats.frag.glsl?raw';
import reinforce from './shaders/reinforce.frag.glsl?raw';
import dryMark from './shaders/dry_mark.frag.glsl?raw';
import dryConfirm from './shaders/dry_confirm.frag.glsl?raw';
import dryShare from './shaders/dry_share.frag.glsl?raw';
import dryApply from './shaders/dry_apply.frag.glsl?raw';
import blur13 from './shaders/blur13.frag.glsl?raw';
import wetMark from './shaders/wet_mark.frag.glsl?raw';
import wetApply from './shaders/wet_apply.frag.glsl?raw';
import view from './shaders/view.frag.glsl?raw';

/** 모든 프래그먼트 셰이더의 머리말. 이웃 접근은 texelFetch 와 정수 나머지로 한다(토러스) */
const COMMON = `#version 300 es
precision highp float;
precision highp int;
precision highp sampler2D;
// 토러스 감김. q 는 -n 이상이어야 한다
ivec2 wr(ivec2 q, ivec2 n) { return (q + n) % n; }`;

/** 9점 연산자의 가중치 합과 이웃 합. 간선 채널은 E, N, NE, SE 이고 반대 방향 간선은 이웃 셀이 갖고 있다 */
const MG_FN = `void mgStencil(ivec2 c, ivec2 n, out float wsum, out float nbr) {
  ivec2 e = wr(c + ivec2(1, 0), n), w = wr(c + ivec2(-1, 0), n), nn = wr(c + ivec2(0, 1), n), s = wr(c + ivec2(0, -1), n);
  ivec2 ne = wr(c + ivec2(1, 1), n), sw = wr(c + ivec2(-1, -1), n), se = wr(c + ivec2(1, -1), n), nw = wr(c + ivec2(-1, 1), n);
  vec4 w0 = texelFetch(uW, c, 0);
  float wW = texelFetch(uW, w, 0).r, wS = texelFetch(uW, s, 0).g, wSW = texelFetch(uW, sw, 0).b, wNW = texelFetch(uW, nw, 0).a;
  wsum = w0.r + wW + w0.g + wS + w0.b + wSW + w0.a + wNW;
  nbr = w0.r * texelFetch(uP, e, 0).r + wW * texelFetch(uP, w, 0).r + w0.g * texelFetch(uP, nn, 0).r + wS * texelFetch(uP, s, 0).r
      + w0.b * texelFetch(uP, ne, 0).r + wSW * texelFetch(uP, sw, 0).r + w0.a * texelFetch(uP, se, 0).r + wNW * texelFetch(uP, nw, 0).r;
}`;

export type ShaderVars = Record<string, string>;

function make(src: string, vars: ShaderVars): string {
  return resolveShader(src, { COMMON, MG_FN, ...vars });
}

export function multigridShaders(vars: ShaderVars) {
  return {
    jacobi: make(mgJacobi, vars),
    residual: make(mgResidual, vars),
    restrict: make(mgRestrict, vars),
    prolong: make(mgProlong, vars),
    coarsen: make(mgCoarsen, vars),
  };
}

export function plasmShaders(vars: ShaderVars) {
  return {
    edgeActivate: make(edgeActivate, vars),
    phase: make(phase, vars),
    rest: make(rest, vars),
    mgInit: make(mgInit, vars),
    flux: make(flux, vars),
    reduceQ0: make(reduceQ0, vars),
    reduceSum: make(reduceSum, vars),
    reduceStats: make(reduceStats, vars),
    reinforce: make(reinforce, vars),
    dryMark: make(dryMark, vars),
    dryConfirm: make(dryConfirm, vars),
    dryShare: make(dryShare, vars),
    dryApply: make(dryApply, vars),
    blur: make(blur13, vars),
    wetMark: make(wetMark, vars),
    wetApply: make(wetApply, vars),
    view: make(view, vars),
  };
}
