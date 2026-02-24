// 블롭 본체 프래그먼트 셰이더 — .glsl + 플레이스홀더 치환

import blobBodyFragSrc from './glsl/blob_body.frag.glsl?raw';
import { resolveShader } from '../shaderUtils';
import { BLOB_BODY } from '../../config';

const B = BLOB_BODY;
const ab = B.ACTIVE_BASE, ad = B.ACTIVE_DARK;
const db = B.DORMANT_BASE, dd = B.DORMANT_DARK;
const mc = B.MEMBRANE_COLOR, dm = B.DORMANT_MEMBRANE;

export const BLOB_BODY_FRAG = resolveShader(blobBodyFragSrc, {
  FADE_START: B.FADE_START.toFixed(1),
  NOISE_FLOOR: B.NOISE_FLOOR.toFixed(2),
  MEMBRANE_ALPHA: B.MEMBRANE_ALPHA.toFixed(3),
  DILATE_RADIUS: B.DILATE_RADIUS.toFixed(1),
  MAX_VALUE: B.MAX_VALUE.toFixed(1),
  ACTIVE_BASE_R: (ab.r / 255).toFixed(3),
  ACTIVE_BASE_G: (ab.g / 255).toFixed(3),
  ACTIVE_BASE_B: (ab.b / 255).toFixed(3),
  ACTIVE_DARK_R: (ad.r / 255).toFixed(3),
  ACTIVE_DARK_G: (ad.g / 255).toFixed(3),
  ACTIVE_DARK_B: (ad.b / 255).toFixed(3),
  MEMBRANE_R: (mc.r / 255).toFixed(3),
  MEMBRANE_G: (mc.g / 255).toFixed(3),
  MEMBRANE_B: (mc.b / 255).toFixed(3),
  DORMANT_BASE_R: (db.r / 255).toFixed(3),
  DORMANT_BASE_G: (db.g / 255).toFixed(3),
  DORMANT_BASE_B: (db.b / 255).toFixed(3),
  DORMANT_DARK_R: (dd.r / 255).toFixed(3),
  DORMANT_DARK_G: (dd.g / 255).toFixed(3),
  DORMANT_DARK_B: (dd.b / 255).toFixed(3),
  DORMANT_MEMBRANE_R: (dm.r / 255).toFixed(3),
  DORMANT_MEMBRANE_G: (dm.g / 255).toFixed(3),
  DORMANT_MEMBRANE_B: (dm.b / 255).toFixed(3),
});
