terraform {
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "0.6.0" #don't specify version if you always want to use the latest
    }
  }
}