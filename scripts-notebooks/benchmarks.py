# scripts/benchmark.py

import asyncio
import os
import sys
import time
from statistics import mean, median
from typing import Any, Dict

# Agregar la raíz del proyecto al sys.path para importar los módulos de app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.backend.schemas.chat import ChatRequest
from app.backend.services.dispute_service import dispute_service
from app.backend.services.task_handlers import (
    handle_consolidate_financial_summary,
)


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


async def measure_task_handler_batch_vs_sequential(num_items: int = 50):
    """Compara la ejecución del Task Handler procesando registros uno por uno

    frente al procesamiento optimizado en lote (batch).
    """
    request = ChatRequest(
        message="Consolidar resumen financiero",
        session_id="BENCHMARK_S3_BATCH",
    )

    # Creamos un conjunto de productos/transacciones ficticios para la prueba
    mock_products = [
        {"product_id": f"P_{i}", "current_balance": 1500.50 + i}
        for i in range(num_items)
    ]

    # 1. Ejecución Secuencial: Procesar llamando al handler por cada elemento
    start_seq = time.perf_counter()
    for item in mock_products:
        single_context: Dict[str, Any] = {
            "products": [item],
            "exchange_rate_usd": 1.0,
            "recent_transactions": [],
            "active_complaints": [],
        }
        await handle_consolidate_financial_summary(
            context=single_context,
            request=request,
            entities={},
        )
    seq_time = (time.perf_counter() - start_seq) * 1000.0

    # 2. Ejecución Batch: Procesar todo el conjunto en una sola
    # invocación del Task Handler
    batch_context: Dict[str, Any] = {
        "products": mock_products,
        "exchange_rate_usd": 1.0,
        "recent_transactions": [],
        "active_complaints": [],
    }
    start_batch = time.perf_counter()
    await handle_consolidate_financial_summary(
        context=batch_context,
        request=request,
        entities={},
    )
    batch_time = (time.perf_counter() - start_batch) * 1000.0

    improvement = ((seq_time - batch_time) / seq_time) * 100.0 if seq_time > 0 else 0.0

    return seq_time, batch_time, improvement


async def run_benchmark():
    message = "Quiero ver mi resumen de cuenta"
    single_iterations = 10
    concurrent_rounds = 5

    print("=" * 80)
    print(" 🚀 BENCHMARK METRICAS: TASK HANDLERS BATCH VS SECUENCIAL & CONCURRENCIA")
    print("=" * 80)
    print(f"Mensaje de prueba: '{message}'\n")

    # -------------------------------------------------------------
    # 1. EVALUACIÓN DE PETICIÓN ÚNICA
    # -------------------------------------------------------------
    print("[1/3] Evaluando latencia individual (1 usuario)...")

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
    diff_single = ((avg_seq - avg_graph) / avg_seq) * 100.0 if avg_seq > 0 else 0.0

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
        f"[2/3] Evaluando media y mediana con múltiples "
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
        c_avg_graph = mean(graph_rounds)
        c_med_graph = median(graph_rounds)

        speedup_avg = (
            ((c_avg_seq - c_avg_graph) / c_avg_seq) * 100.0 if c_avg_seq > 0 else 0.0
        )
        str_seq = f"{c_avg_seq:.1f} / {c_med_seq:.1f}"
        str_graph = f"{c_avg_graph:.1f} / {c_med_graph:.1f}"

        print(
            f"{concurrency:<10} | {str_seq:<30} "
            f"| {str_graph:<28} | {speedup_avg:<10.1f}%"
        )

    print("-" * len(header))
    print("\n")

    # -------------------------------------------------------------
    # 3. EVALUACIÓN DIRECTA DEL TASK HANDLER: SECUENCIAL VS BATCH
    # -------------------------------------------------------------
    print("[3/3] Evaluando Task Handler: Procesamiento Secuencial vs por Batches...")

    num_records = 50
    (
        seq_th_time,
        batch_th_time,
        th_improvement,
    ) = await measure_task_handler_batch_vs_sequential(num_items=num_records)

    print(
        f"  • Task Handler Secuencial ({num_records} llamadas) -> {seq_th_time:.2f} ms"
    )
    print(f"  • Task Handler en Lote / Batch (1 llamada)    -> {batch_th_time:.2f} ms")
    print(f"  ⚡ Eficiencia del Task Handler en Batches: {th_improvement:.1f}%\n")

    print("Benchmark completado con éxito.\n")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
