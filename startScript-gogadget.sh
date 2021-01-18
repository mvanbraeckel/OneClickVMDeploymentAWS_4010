#!/bin/bash

# golang gogadget start script
# For container: image golang, which creates image and container gogadget
# Purpose: When run, prints "Go-Go-Gadget Cloud!", then "Wowsers!"

cat > main.go << EOF
package main
import "fmt"

func main() {
  for i := 1; i<=2; i++ {
    fmt.Printf("Go-")
  }
  fmt.Printf("Gadget Cloud!\n")
  fmt.Println("Wowsers!")
}
EOF

cat > Dockerfile << EOF
FROM golang
RUN mkdir /usr/app
ADD . /usr/app/
WORKDIR /usr/app
RUN go build -o main .
CMD ["./main"]
EOF

sudo docker build -t gogadget . -f Dockerfile
sudo docker run gogadget
