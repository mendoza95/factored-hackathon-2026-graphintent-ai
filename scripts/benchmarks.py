# scripts/benchmark.py

import asyncio
import os
import sys
import time
from statistics import mean, median

# Agregar la raíz del proyecto al sys.path para importar los módulos de app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.backend.schemas.chat import ChatRequest
from app.backend.services.dispute_service import dispute_service


async def measure_single_request(message: str, use_graph: bool) -> float:
    """Mide el tiempo de ejecución en milisegundos de una sola petición."""
    request = ChatRequest(
        message=message,
        session_id="BENCHMARK_SESS_SINGLE",
    )
    start = time.perf_counter()
    await dispute_service.process_chat_message(request, use_graph=use_graph)
    return (time.perf_counter() - start) * 1000.0


async def run_concurrent_users(num_users: int, message: str, use_graph: bool) -> float:
    """Simula N usuarios enviando peticiones en paralelo en una sola corrida."""
    tasks = [
        dispute_service.process_chat_message(
            ChatRequest(
                message=message,
                session_id=f"BENCHMARK_SESS_{i}",
            ),
            use_graph=use_graph,
        )
        for i in range(num_users)
    ]
    start_total = time.perf_counter()
    await asyncio.gather(*tasks)
    return (time.perf_counter() - start_total) * 1000.0


async def run_benchmark():
    message = "Quiero ver mi resumen de cuenta"
    single_iterations = 10
    concurrent_rounds = 5  # Número de corridas por nivel de concurrencia

    print("=" * 80)
    print(" 🚀 BENCHMARK METRICAS: EJECUCIÓN SECUENCIAL VS GRAFO CONCURRENTE")
    print("=" * 80)
    print(f"Mensaje de prueba: '{message}'\n")

    # -------------------------------------------------------------
    # 1. EVALUACIÓN DE PETICIÓN ÚNICA
    # -------------------------------------------------------------
    print("[1/2] Evaluando latencia individual (1 usuario)...")

    # Warm-up (descarte de latencia inicial)
    await measure_single_request(message, use_graph=False)
    await measure_single_request(message, use_graph=True)

    seq_times = []
    graph_times = []

    for _ in range(single_iterations):
        seq_times.append(await measure_single_request(message, use_graph=False))
        graph_times.append(await measure_single_request(message, use_graph=True))

    avg_seq = mean(seq_times)
    med_seq = median(seq_times)
    avg_graph = mean(graph_times)
    med_graph = median(graph_times)
    diff_single = ((avg_seq - avg_graph) / avg_seq) * 100.0

    print(
        f"  • Secuencial       -> Media: {avg_seq:.2f} ms | Mediana: {med_seq:.2f} ms"
    )
    print(
        f"  • Grafo Concurrente -> Media: {avg_graph:.2f} ms "
        f"| Mediana: {med_graph:.2f} ms"
    )
    print(f"  ⚡ Reducción de latencia base: {diff_single:.1f}%\n")

    # -------------------------------------------------------------
    # 2. EVALUACIÓN DE ESTADÍSTICAS BAJO CARGA CONCURRENTE
    # -------------------------------------------------------------
    print(
        f"[2/2] Evaluando media y mediana con múltiples "
        f"usuarios ({concurrent_rounds} rondas por nivel)..."
    )
    concurrency_levels = [5, 10, 25, 50]

    header = (
        f"{'Usuarios':<10} | {'Secuencial Media/Mediana (ms)':<30} "
        f"| {'Grafo Media/Mediana (ms)':<28} | {'Mejora (%)':<10}"
    )
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    for concurrency in concurrency_levels:
        seq_rounds = []
        graph_rounds = []

        for _ in range(concurrent_rounds):
            seq_rounds.append(
                await run_concurrent_users(concurrency, message, use_graph=False)
            )
            graph_rounds.append(
                await run_concurrent_users(concurrency, message, use_graph=True)
            )

        c_avg_seq = mean(seq_rounds)
        c_med_seq = median(seq_rounds)

        str_seq = f"{c_avg_seq:.1f} / {c_med_seq:.1f}"

        print(
            f"{concurrency:<10} | {str_seq:<30} "
            "| {str_graph:<28} | {speedup_avg:<10.1f}%"
        )

    print("-" * len(header))
    print("\nBenchmark completado con éxito.\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
