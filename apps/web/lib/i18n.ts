import ru from "@/messages/ru.json";
import uz from "@/messages/uz.json";

export const locales = ["uz", "ru"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "uz";

export type Messages = typeof uz;

const dictionaries: Record<Locale, Messages> = { uz, ru };

export function isLocale(value: string): value is Locale {
  return locales.includes(value as Locale);
}

export function getMessages(locale: Locale): Messages {
  return dictionaries[locale];
}

export function localeLabel(locale: Locale): string {
  return locale === "uz" ? "O‘zbekcha" : "Русский";
}
