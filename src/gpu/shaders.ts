// WebGL2 셰이더 소스 — .glsl 파일에서 로드 (플레이스홀더 없음)

import fullscreenQuadVertSrc from './shaders/glsl/fullscreen_quad.vert.glsl?raw';
import diffuseDecayFragSrc from './shaders/glsl/diffuse_decay.frag.glsl?raw';
import depositBlendFragSrc from './shaders/glsl/deposit_blend.frag.glsl?raw';

export const FULLSCREEN_QUAD_VERT = fullscreenQuadVertSrc;
export const DIFFUSE_DECAY_FRAG = diffuseDecayFragSrc;
export const DEPOSIT_BLEND_FRAG = depositBlendFragSrc;
