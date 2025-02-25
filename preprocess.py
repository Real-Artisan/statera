def convert_cpu(cpu_value):
        if not cpu_value:  # Handle None case
            return None
        if cpu_value.endswith("n"):
            return f"{float(cpu_value[:-1]) / 1000000}m"
        return cpu_value  # Already in millicores

def convert_memory(memory_value):
    if not memory_value:  # Handle None case
        return None
    if memory_value.endswith("Ki"):
        return f"{float(memory_value[:-2]) / 1024}Mi"
    return memory_value  # Already in MiB

def parse_cpu(cpu_value):
    if cpu_value.endswith("m"):
        return float(cpu_value[:-1]) / 1000
    return float(cpu_value)

def parse_memory(memory_value):
    if memory_value.endswith("Mi"):
        return float(memory_value[:-2])
    elif memory_value.endswith("Gi"):
        return float(memory_value[:-2]) * 1024
    return float(memory_value)


def preprocess_metrics(metrics):
    for metric in metrics:
        metric["cpu_usage"] = convert_cpu(metric["cpu_usage"])
        metric["memory_usage"] = convert_memory(metric["memory_usage"])
        metric["cpu_request"] = convert_cpu(metric["cpu_request"])
        metric["cpu_limit"] = convert_cpu(metric["cpu_limit"])
        metric["memory_request"] = convert_memory(metric["memory_request"])
        metric["memory_limit"] = convert_memory(metric["memory_limit"])

    return metrics
