/**
 * chat 域文案（源语言 zh-CN）。
 *
 * 相对时间用**命名插值**（`{n}`）而不是字符串拼接：语序在不同语言里不同
 * （`{n} 分钟前` / `{n} min ago` / `قبل {n} دقيقة`），拼接必然出错。
 */
export default {
  time: {
    justNow: '刚刚',
    minutesAgo: '{n} 分钟前',
    hoursAgo: '{n} 小时前',
  },
}
