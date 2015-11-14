library(dplyr)
library(ggplot2)
library(lme4)
library(broom)

devtools::load_all("dualverification")
# data(dualverification)
# experiment in progress, load from source:
dualverification <- compile("experiment/data/") %>%
  clean %>% 
  recode %>%
  # Combine feat_type and mask_type for colors in the plot
  mutate(feat_mask = paste(feat_type, mask_type, sep = ":"))

# ---- overall-rts-mod
overall_rt <- lmer(rt ~ feat_c * mask_c + (1|subj_id/response_type),
                   data = dualverification)
tidy(overall_rt, effects = "fixed")

# ---- overall-rts-plot
ggplot(dualverification, aes(x = mask_c, y = rt, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
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
ggplot(filter(dualverification, response_type == "prompt"),
       aes(x = mask_c, y = rt, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
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
ggplot(filter(dualverification, response_type == "pic"),
       aes(x = mask_c, y = rt, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  facet_wrap("feat_label") +
  coord_cartesian(ylim = rt_lim) +
  scale_x_mask +
  scale_y_rt +
  scale_fill_featmask +
  base_theme +
  ggtitle("Verify picture")
