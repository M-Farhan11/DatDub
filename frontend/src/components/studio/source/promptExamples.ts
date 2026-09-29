export const PROMPT_EXAMPLES = [
  {
    label: "Online store",
    text: "An online store with customers, orders, order items and payments. Orders can have several items and one payment. Order totals equal the sum of their items.",
  },
  {
    label: "Clinic appointments",
    text: "A clinic with patients, doctors, appointments and invoices. Each appointment belongs to one patient and one doctor. Invoices are issued after the appointment date.",
  },
  {
    label: "SaaS subscriptions",
    text: "A SaaS product with accounts, users, subscriptions and monthly invoices. Each account has several users and one active subscription. Invoice amounts follow the subscription plan.",
  },
]

/** Minimum length before "Draft schema" is enabled. */
export const MIN_PROMPT_LENGTH = 10
