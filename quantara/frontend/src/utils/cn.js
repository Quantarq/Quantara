import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Conditionally join Tailwind CSS classes, merging conflicts via tailwind-merge.
 *
 * @param {...(string|boolean|null|undefined|object|Array)} inputs - Class values
 * @returns {string} Merged class string with conflicts resolved
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
