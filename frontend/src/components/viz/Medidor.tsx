/** Medidor 0-100 para la puntuación de riesgo.
 *
 *  El relleno cambia de tono por banda y la pista es un paso más claro de la
 *  misma rampa, para que el estado se lea a lo largo de toda la barra. El
 *  número siempre va al lado: el color no carga el dato solo.
 */
export function Medidor({ valor }: { valor: number }) {
  const banda = valor >= 70 ? "critico" : valor >= 40 ? "advertencia" : "normal";

  const relleno = {
    critico: "var(--estado-critico)",
    advertencia: "var(--estado-advertencia)",
    normal: "var(--series-1)",
  }[banda];

  const pista = {
    critico: "var(--medidor-pista-critico)",
    advertencia: "var(--medidor-pista-advertencia)",
    normal: "var(--medidor-pista)",
  }[banda];

  const etiqueta = { critico: "riesgo alto", advertencia: "riesgo medio", normal: "riesgo bajo" }[
    banda
  ];

  return (
    <div className="flex items-center gap-2">
      <div
        role="meter"
        aria-valuenow={valor}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Puntuación de riesgo ${valor.toFixed(0)} de 100, ${etiqueta}`}
        className="h-1.5 w-24 shrink-0 overflow-hidden rounded-full"
        style={{ background: pista }}
      >
        <div
          className="h-full rounded-full"
          style={{ width: `${Math.min(valor, 100)}%`, background: relleno }}
        />
      </div>
      <span className="w-8 text-right text-sm font-medium tabular-nums text-[var(--text-primary)]">
        {valor.toFixed(0)}
      </span>
    </div>
  );
}
