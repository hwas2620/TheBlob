// .glsl 파일을 ?raw로 import할 때의 타입 선언
declare module '*.glsl?raw' {
  const src: string;
  export default src;
}
