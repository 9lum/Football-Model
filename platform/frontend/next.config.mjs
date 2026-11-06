import path from 'node:path';import {fileURLToPath} from 'node:url';
export default {output:'export',basePath:process.env.NEXT_PUBLIC_BASE_PATH||'/Football-Model/platform',outputFileTracingRoot:path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),images:{unoptimized:true},trailingSlash:true};
