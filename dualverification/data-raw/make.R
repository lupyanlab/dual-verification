# Compile data files and save to package
library(devtools)
library(dplyr)
library(readr)

load_all()

dualverification <- compile("data-raw/dualverification/") %>%
  clean %>%
  recode

use_data(dualverification)

proposition_ratings <- read_csv("data-raw/proposition_ratings.csv")
use_data(proposition_ratings)
