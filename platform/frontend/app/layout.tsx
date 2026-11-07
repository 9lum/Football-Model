import type {Metadata} from 'next';
import './globals.css';
import AmbientGlass from '../components/ambient-glass';
export const metadata:Metadata={title:'Projections n Shit — NFL Research',description:'NFL player projections, market comparisons, weather and transparent model validation.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en" data-appearance="ember" data-density="compact" data-background-motion="on"><body><AmbientGlass/>{children}</body></html>}
