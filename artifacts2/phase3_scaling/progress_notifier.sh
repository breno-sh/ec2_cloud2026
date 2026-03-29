#!/bin/bash
TARGET=675
DIR1="/home/breno/doutorado/ec2sweetspot_noms2/artifacts2/phase3_scaling/n30_logs"
DIR2="/home/breno/doutorado/ec2sweetspot_noms2/artifacts/phase3_scaling/n30_logs"

while true; do
  COUNT=$(find "$DIR1" "$DIR2" -type f -name "*.log" 2>/dev/null | wc -l)
  PERCENT=$(echo "scale=2; ($COUNT / $TARGET) * 100" | bc)
  
  # Send Ubuntu desktop notification
  notify-send "🚀 IEEE CLOUD Benchmark" "Progresso da Fase 3: $COUNT de $TARGET logs concluidos ($PERCENT%)." --icon=dialog-information
  
  if [ "$COUNT" -ge "$TARGET" ]; then
    notify-send "✅ Benchmark Concluído!" "Todos os 675 testes foram finalizados." --icon=dialog-information
    break
  fi
  
  # Wait 10 minutes
  sleep 600
done
