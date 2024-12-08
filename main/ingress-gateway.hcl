Kind = "ingress-gateway"
Name = "api-gateway"
Listeners = [
  {
    Port     = 8080
    Protocol = "http"
    Services = [
      {
        Name  = "product_service"
        Hosts = ["*"]  # Obsługuj wszystkie hosty
      }
    ]
  }
]
