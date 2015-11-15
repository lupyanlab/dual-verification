# Compile data files and save to package
library(devtools)
library(dplyr)
load_all()

dualverification <- compile("data-raw/dualverification/") %>%
  clean %>%
  recode

use_data(dualverification)
