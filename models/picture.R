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

# ---- pic-mod
pic_mod <- glmer(is_error ~ feat_c * mask_c + (1|subj_id),
                 data = filter(dualverification, response_type == "pic"),
                 family = binomial)
tidy(pic_mod, effects = "fixed") %>%
  add_sig_stars

# ---- pic-plot
ggplot(filter(dualverification, response_type == "pic"),
       aes(x = mask_c, y = is_error, fill = feat_mask)) +
  geom_bar(stat = "summary", fun.y = "mean", alpha = 0.6) +
  facet_wrap("feat_label") +
  scale_x_mask +
  scale_y_error +
  scale_fill_featmask +
  base_theme +
  ggtitle("Verify picture")
