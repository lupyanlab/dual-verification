library(dplyr)
library(ggplot2)
library(scales)
library(tidyr)

devtools::load_all("dualverification")
data(dualverification)

# Proposition
propositions <- dualverification %>%
  group_by(proposition_id) %>%
  summarize(
    count = n(),
    rt = mean(rt, na.rm = TRUE),
    accuracy = mean(is_correct, na.rm = TRUE),
    num_timeout = sum(response == "timeout")
  ) %>%
  mutate(
    rank_rt = rank(rt),
    rank_accuracy = rank(accuracy, ties = "first")
  )

proposition_rt_levels <- propositions %>%
  arrange(rt) %>%
  .$proposition_id
propositions$proposition_id_rt <- factor(propositions$proposition_id,
                                         levels = proposition_rt_levels)

proposition_accuracy_levels <- propositions %>%
  arrange(accuracy) %>%
  .$proposition_id
propositions$proposition_id_accuracy <- factor(propositions$proposition_id,
                                               levels = proposition_accuracy_levels)

rank_axis_breaks <- c(1, seq(5, nrow(propositions), by = 5))
scale_x_rank <- scale_x_continuous("Rank", breaks = rank_axis_breaks)
rank_xlim <- c(0.5, nrow(propositions) + 2.5)
descriptives_theme <- theme_minimal() +
  theme(
    axis.ticks = element_blank(),
    legend.position = "none"
  )

ggplot(propositions, aes(x = rank_rt, y = rt, fill = proposition_id_rt)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = proposition_id), hjust = 0, angle = 90, size = 3) +
  scale_x_rank +
  scale_y_continuous("Average RT (ms)") +
  coord_cartesian(xlim = rank_xlim, ylim = c(100, 1500)) +
  descriptives_theme
ggsave("descriptives/propositions-rt.png", width = 20)

ggplot(propositions, aes(x = rank_accuracy, y = accuracy, fill = proposition_id_accuracy)) +
  geom_bar(stat = "identity") +
  geom_text(aes(label = proposition_id), hjust = 0, angle = 90, size = 3) +
  scale_x_rank +
  scale_y_continuous("Accuracy", labels = percent) +
  coord_cartesian(xlim = rank_xlim, ylim = c(0, 1.5)) +
  descriptives_theme
ggsave("descriptives/propositions-error.png", width = 20)

propositions_parallel <- propositions %>%
  select(proposition_id_accuracy, rank_rt, rank_accuracy) %>%
  gather(rank_type, rank_value, -proposition_id_accuracy) %>%
  mutate(rank_type = factor(rank_type, levels = c("rank_accuracy", "rank_rt")))

ggplot(propositions_parallel, aes(x = rank_type, y = rank_value)) +
  geom_line(aes(group = proposition_id_accuracy, color = proposition_id_accuracy)) +
  geom_text(aes(label = proposition_id_accuracy),
            data = filter(propositions_parallel, rank_type == "rank_accuracy"),
            hjust = 1, alpha = 0.4, size = 2) +
  scale_x_discrete("", labels = c("Accuracy", "RT")) +
  scale_y_continuous("Rank", breaks = rank_axis_breaks) +
  descriptives_theme
ggsave("descriptives/propositions-parallel.png", height = 10)
