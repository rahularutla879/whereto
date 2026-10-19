export function HeroArtwork() {
  return (
    <svg className="hero-art" viewBox="0 0 460 350" fill="none" aria-hidden="true">
      <defs><pattern id="grid" width="28" height="28" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#d3d5c5" /></pattern></defs>
      <rect x="18" y="17" width="425" height="310" rx="155" fill="url(#grid)" />
      <path d="M105 200C28 94 242 59 269 125C307 220 139 307 275 277C336 265 392 221 362 153" stroke="#a9b4a0" strokeWidth="2" strokeDasharray="7 8" />
      <g transform="rotate(-12 112 121)">
        <rect x="40" y="53" width="139" height="138" rx="19" fill="#e8a57f" />
        <rect x="47" y="46" width="139" height="138" rx="19" fill="#f6bf9e" stroke="#263f32" strokeWidth="1.4" />
        <path d="M84 80c-6 7-3 14 1 23l-4 30c-1 13 18 16 21 3l2-31c8-10 10-17 6-25Z" fill="#fff9eb" stroke="#263f32" strokeWidth="2" />
        <path d="m84 98 20 4m-21 3 20 4" stroke="#d76d43" strokeWidth="4" />
        <circle cx="133" cy="129" r="24" fill="#314f3d" />
        <circle cx="130" cy="117" r="3" fill="#f6bf9e" /><circle cx="120" cy="124" r="3" fill="#f6bf9e" /><circle cx="132" cy="128" r="3" fill="#f6bf9e" />
        <path d="M62 163h48" stroke="#263f32" strokeWidth="2" strokeLinecap="round" />
        <text x="126" y="167" fontSize="10" fill="#263f32" fontFamily="monospace">01</text>
      </g>
      <g transform="rotate(11 328 136)">
        <rect x="266" y="67" width="139" height="138" rx="19" fill="#b8b0d8" />
        <rect x="260" y="59" width="139" height="138" rx="19" fill="#d7cfeb" stroke="#263f32" strokeWidth="1.4" />
        <path d="m302 91 51 0-23 36v28m-14 0h28" stroke="#263f32" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="m307 100 41 0-18 27Z" fill="#fff9eb" /><path d="m337 104 17-27" stroke="#d76d43" strokeWidth="3" strokeLinecap="round" />
        <circle cx="351" cy="94" r="10" fill="#b8c79c" stroke="#263f32" strokeWidth="1.5" />
        <path d="M276 178h48" stroke="#263f32" strokeWidth="2" strokeLinecap="round" /><text x="353" y="182" fontSize="10" fill="#263f32" fontFamily="monospace">02</text>
      </g>
      <g transform="rotate(-5 218 252)">
        <rect x="151" y="189" width="149" height="137" rx="19" fill="#a5b89b" />
        <rect x="145" y="183" width="149" height="137" rx="19" fill="#ced9b5" stroke="#263f32" strokeWidth="1.4" />
        <path d="m183 222 66 0-8 54h-50Z" fill="#fff9eb" stroke="#263f32" strokeWidth="2" />
        <path d="m199 223 3 52m14-52v52m17-52-4 52" stroke="#dc7b55" strokeWidth="8" />
        <path d="M181 221c-7-11 2-19 11-16-1-14 18-18 23-7 9-13 27-6 26 5 12-3 20 9 10 18Z" fill="#fff9eb" stroke="#263f32" strokeWidth="2" strokeLinejoin="round" />
        <path d="M162 301h48" stroke="#263f32" strokeWidth="2" strokeLinecap="round" /><text x="250" y="305" fontSize="10" fill="#263f32" fontFamily="monospace">03</text>
      </g>
      <path d="m222 43 2 9m-15-2 8 5m18-9-7 8M369 258l3 12m-15-4 10 7m15-15-7 12M77 247l-3 10m-9-10 5 7" stroke="#d7744f" strokeWidth="2.5" strokeLinecap="round" />
      <g transform="rotate(-8 87 290)"><rect x="31" y="276" width="110" height="26" rx="13" fill="#fffdf7" stroke="#d5d5c7" /><text x="45" y="293" fontSize="11" fill="#314f3d" fontFamily="sans-serif">good times ahead ↗</text></g>
    </svg>
  );
}

export function CardArtwork({ theme }: { theme: "peach" | "lavender" | "mint" }) {
  return <svg viewBox="0 0 400 145" fill="none" aria-hidden="true" className="card-art">
    <path d="M0 120C70 76 121 156 208 121C288 88 339 116 400 84" stroke="currentColor" strokeOpacity=".12" strokeWidth="1.5" />
    <circle cx="320" cy="27" r="68" stroke="currentColor" strokeOpacity=".08" /><circle cx="320" cy="27" r="91" stroke="currentColor" strokeOpacity=".08" />
    {theme === "peach" ? <g transform="translate(153 17) rotate(9 50 65)">
      <path d="M23 10c-8 8-4 18 1 29L15 91c-4 23 27 27 29 4l1-55C55 25 53 17 47 9Z" fill="#fff8e9" stroke="#374d3a" strokeWidth="2" />
      <path d="m23 34 23 3m-24 4 23 3" stroke="#d46f49" strokeWidth="5" />
      <path d="M58 25c-7 8-4 15 0 24l-5 39c-2 21 26 22 26 2l-1-40c9-11 8-19 3-25Z" fill="#fff8e9" stroke="#374d3a" strokeWidth="2" />
      <path d="m57 44 23 0m-23 7h22" stroke="#d46f49" strokeWidth="4" />
      <circle cx="95" cy="94" r="29" fill="#314f3d" /><circle cx="92" cy="80" r="3.5" fill="#efbc9d" /><circle cx="82" cy="90" r="3.5" fill="#efbc9d" /><circle cx="96" cy="92" r="3.5" fill="#efbc9d" />
    </g> : theme === "lavender" ? <g transform="translate(130 19)">
      <path d="m17 30 62 0-29 43v33m-16 0h33" stroke="#374d3a" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="m24 40 48 0-22 33Z" fill="#fff8e9" /><path d="m54 48 23-37" stroke="#d46f49" strokeWidth="3" strokeLinecap="round" />
      <circle cx="77" cy="32" r="13" fill="#c5cf9a" stroke="#374d3a" strokeWidth="1.5" />
      <g transform="rotate(12 106 70)"><path d="m86 30 43 0-6 59c-2 20-29 20-31 0Z" fill="#fff8e9" stroke="#374d3a" strokeWidth="2" /><path d="m93 50 29 0-4 37c-1 12-20 12-21 0Z" fill="#dd9a6f" /><path d="m110 44 8-33" stroke="#374d3a" strokeWidth="2" /><path d="m101 55 14 8m-13 12 14-8" stroke="#fff8e9" strokeWidth="3" /></g>
    </g> : <g transform="translate(146 20) rotate(-9 50 55)">
      <rect x="5" y="32" width="107" height="72" rx="6" fill="#fff8e9" stroke="#374d3a" strokeWidth="2" />
      <path d="m4 32 105-20-5-20L0 12Z" fill="#314f3d" stroke="#374d3a" strokeWidth="2" />
      <path d="m15 9 16 19m13-25 16 19m13-25 16 19" stroke="#fff8e9" strokeWidth="11" />
      <path d="m46 52 27 15-27 16Z" fill="#d47b57" /><path d="M20 92h26" stroke="#314f3d" strokeWidth="2" strokeLinecap="round" />
    </g>}
    <path d="m100 47 2 8m-10-2 7 5m14-13-7 9M296 93l2 8m-10-2 7 5m14-13-7 9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
  </svg>;
}
