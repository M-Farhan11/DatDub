import { createCn } from "cn/config"

/**
 * Class merging that knows our custom font sizes (globals.css `--text-*`).
 * Without this, `text-code-md` + `text-ink` would be treated as two font
 * sizes and the size class would be dropped.
 */
export const cn = createCn({
  extend: {
    classGroups: {
      "font-size": [
        {
          text: [
            "display",
            "display-xl",
            "headline-xl",
            "headline-lg",
            "headline-md",
            "headline-sm",
            "body-lg",
            "body-md",
            "body-sm",
            "label-lg",
            "label-md",
            "code-md",
            "code-sm",
          ],
        },
      ],
    },
  },
})
