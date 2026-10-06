// Daily reading schedule.
//
// The calendar itself is resolved in Python (src/content.py) and exported as
// `daily`: daily[slug][day - 1] is the article for that day of the year. The
// browser only has to find today's day-of-year, so both platforms always show
// the same article without reimplementing the fallback rule.

export function dayOfYear(date = new Date()) {
  const start = Date.UTC(date.getFullYear(), 0, 1);
  const here = Date.UTC(date.getFullYear(), date.getMonth(), date.getDate());
  return Math.floor((here - start) / 86400000) + 1;
}

export function scheduleDay(day, daysInYear = 365) {
  return Math.min(Math.max(Math.trunc(day), 1), daysInYear);
}

export function dailyArticleId(daily, slug, day, daysInYear = 365) {
  const list = (daily && daily[slug]) || [];
  if (!list.length) return null;
  const slot = scheduleDay(day, daysInYear);
  return list[(slot - 1) % list.length];
}

export function dateLabel(date = new Date()) {
  return `${date.getMonth() + 1}月${date.getDate()}日`;
}
