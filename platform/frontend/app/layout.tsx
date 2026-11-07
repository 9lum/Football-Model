import type {Metadata} from 'next';
import './globals.css';
import {zoomBootstrap} from '../../../web/display-zoom.mjs';
import AmbientGlass from '../components/ambient-glass';
export const metadata:Metadata={title:'Projections n Shit — NFL Research',description:'NFL player projections, market comparisons, weather and transparent model validation.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html suppressHydrationWarning lang="en" data-appearance="ember" data-density="compact" data-background-motion="on"><body><script dangerouslySetInnerHTML={{__html:zoomBootstrap}}/><AmbientGlass/>{children}</body></html>}
