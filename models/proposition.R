library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
data(dualverification)

# ---- proposition-mod
prompt_mod <- glmer(is_error ~ feat_c * mask_c + (1|subj_id),
                    data = filter(dualverification, response_type == "prompt"),
                    family = binomial)
tidy(prompt_mod, effect = "fixed") %>%
  add_sig_stars

# ---- proposition-plot
pred_error <- format_mod_preds(prompt_mod)

ggplot(filter(dualverification, response_type == "prompt"),
       aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_pointrange(aes(y = estimate, ymin = estimate-se, ymax = estimate+se),
                 data = pred_error) +
  facet_wrap("feat_label") +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme +
  ggtitle("Answer proposition")
