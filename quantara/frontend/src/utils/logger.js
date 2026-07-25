const write = (method, args) => {
  if (import.meta.env.DEV) console[method](...args);
};

export const logger = {
  debug: (...args) => write('debug', args),
  error: (...args) => write('error', args),
  log: (...args) => write('log', args),
  warn: (...args) => write('warn', args),
};