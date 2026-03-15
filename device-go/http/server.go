package http

import (
    "fmt"
    "log"
    "net/http"

    "github.com/gorilla/mux"
)

type Server struct {
    router *mux.Router
    port   int
}

func NewServer(handlers *Handlers, port int) *Server {
    r := mux.NewRouter()
    r.HandleFunc("/api/commands", handlers.SendCommand).Methods("POST")
    r.HandleFunc("/api/commands/list", handlers.ListCommands).Methods("GET") // новый эндпоинт
    r.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        w.Write([]byte("OK"))
    }).Methods("GET")

    return &Server{
        router: r,
        port:   port,
    }
}

func (s *Server) Start() error {
    addr := fmt.Sprintf(":%d", s.port)
    log.Printf("HTTP server listening on %s", addr)
    return http.ListenAndServe(addr, s.router)
}