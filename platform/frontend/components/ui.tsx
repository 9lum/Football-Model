import {clsx} from 'clsx';import {twMerge} from 'tailwind-merge';
export const cn=(...values:any[])=>twMerge(clsx(values));
export function Card({children,className,...props}:{children:React.ReactNode,className?:string,[key:string]:any}){return <section className={cn('card',className)} {...props}>{children}</section>}
export function Badge({children,tone='neutral'}:{children:React.ReactNode,tone?:string}){return <span className={'badge '+tone}>{children}</span>}
export function Empty({children}:{children:React.ReactNode}){return <div className="empty">{children}</div>}
export function Metric({label,value,note}:{label:string,value:React.ReactNode,note?:string}){return <Card><div className="eyebrow">{label}</div><div className="metric">{value}</div>{note&&<p className="muted small">{note}</p>}</Card>}
