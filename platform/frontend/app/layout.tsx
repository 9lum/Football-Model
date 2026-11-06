import type {Metadata} from 'next';
import './globals.css';
export const metadata:Metadata={title:'Projections n Shit — NFL Research',description:'NFL player projections, market comparisons, weather and transparent model validation.'};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>}
