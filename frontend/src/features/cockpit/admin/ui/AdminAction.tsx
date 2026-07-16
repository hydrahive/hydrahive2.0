import { forwardRef, type ButtonHTMLAttributes } from "react"
import { adminActionClass, type AdminActionTone } from "./adminActionClass"

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: AdminActionTone
}

export const AdminAction = forwardRef<HTMLButtonElement, Props>(function AdminAction(
  { tone = "default", className, type = "button", ...props },
  ref,
) {
  return <button ref={ref} type={type} {...props} className={adminActionClass(tone, className)} />
})
