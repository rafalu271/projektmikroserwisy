Kind = "ingress-gateway"
Name = "api-gateway"
Listeners = [
  {
    Port     = 8080
    Protocol = "http"
    Services = [
      {
        Name = "products-service"
        Hosts = ["products-service.api.esklep.com"]
      },
      {
        Name = "orders-service"
        Hosts = ["orders-service.api.esklep.com"]
      }
    ]
  }
]
