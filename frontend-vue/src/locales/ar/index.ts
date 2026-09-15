import chat from './chat'
import errors from './errors'
import legacy from './legacy'

/**
 * ar（RTL）。键与 zh-CN 一一对应（zh-CN 为源语言）；缺失的键会自动回退到 zh-CN。
 * 注意：RTL 由 <html dir="rtl"> 驱动（见 src/i18n/index.ts），新增样式请用逻辑属性
 * （margin-inline-*、padding-inline-*、inset-inline-*），不要写物理方向属性。
 * legacy 目前为空（存量抽取的模板文案待翻译），见 locales/ar/legacy.ts 的说明。
 */
export default {
  common: {
    confirm: 'تأكيد',
    cancel: 'إلغاء',
    save: 'حفظ',
    delete: 'حذف',
    edit: 'تعديل',
    search: 'بحث',
    refresh: 'تحديث',
    loading: 'جارٍ التحميل…',
    empty: 'لا توجد بيانات',
    retry: 'إعادة المحاولة',
    close: 'إغلاق',
    copy: 'نسخ',
    copied: 'تم النسخ',
    language: 'اللغة',
    unknownError: 'خطأ غير معروف',
  },
  chat,
  errors,
  legacy,
}
