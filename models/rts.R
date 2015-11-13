library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
# data(dualverification)
# experiment in progress, load from source:
dualverification <- compile("experiment/data/") %>%
  clean %>% 
  recode

# ---- overall-rts-mod
overall_rt <- lmer(rt ~ feat_c * mask_c + response_c + (1|subj_id),
                   data = dualverification)
tidy(overall_rt, effects = "fixed")

# ---- overall-rts-plot
overall_error <- format_mod_preds(overall_rt)

ggplot(dualverification, aes(x = mask_c, y = rt, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_pointrange(aes(y = estimate, ymin = estimate-se, ymax = estimate+se),
                  data = overall_error) +
  facet_grid(feat_label ~ response_label) +
  coord_cartesian(ylim = rt_lim) +
  scale_x_mask +
  scale_y_rt +
  scale_fill_featmask +
  base_theme

# ---- proposition-rts-mod
prompt_rt <- lmer(rt ~ feat_c * mask_c + (1|subj_id),
                  data = filter(dualverification, response_type == "prompt"))
tidy(prompt_rt, effects = "fixed")

# ---- proposition-rts-plot
prompt_error <- format_mod_preds(prompt_rt)

ggplot(filter(dualverification, response_type == "prompt"),
       aes(x = mask_c, y = rt, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_pointrange(aes(y = estimate, ymin = estimate-se, ymax = estimate+se),
                  data = prompt_error) +
  facet_wrap("feat_label") +
  coord_cartesian(ylim = rt_lim) +
  scale_x_mask +
  scale_y_rt +
  scale_fill_featmask +
  base_theme +
  ggtitle("Answer proposition")

# ---- picture-rts-mod
pic_rt <- lmer(rt ~ feat_c * mask_c + (1|subj_id),
               data = filter(dualverification, response_type == "pic"))
tidy(pic_rt, effects = "fixed")

# ---- picture-rts-plot
pic_error <- format_mod_preds(pic_rt)

ggplot(filter(dualverification, response_type == "pic"),
       aes(x = mask_c, y = rt, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  geom_pointrange(aes(y = estimate, ymin = estimate-se, ymax = estimate+se),
                  data = pic_error) +
  facet_wrap("feat_label") +
  coord_cartesian(ylim = rt_lim) +
  scale_x_mask +
  scale_y_rt +
  scale_fill_featmask +
  base_theme +
  ggtitle("Verify picture")
