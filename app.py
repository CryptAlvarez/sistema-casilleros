
import streamlit as st
import pandas as pd
from supabase import create_client
from io import BytesIO
import math

# =====================================
# CONFIG
# =====================================

st.set_page_config(
    page_title="Sistema de Casilleros",
    layout="wide"
)

# =====================================
# SUPABASE
# =====================================

url = "SUPABASE_URL"

key = "SUPABASE_KEY"

supabase = create_client(url, key)


# =====================================
# TÍTULO
# =====================================

st.title("Sistema de Casilleros")

# =====================================
# PAGINACIÓN
# =====================================

REGISTROS_POR_PAGINA = 50

# =====================================
# CASILLEROS
# =====================================

casilleros = []

inicio = 0
limite = 1000

while True:

    respuesta = supabase.table(
        "casilleros"
    ).select("*") \
     .range(
        inicio,
        inicio + limite - 1
     ) \
     .execute()

    datos = respuesta.data

    if not datos:
        break

    casilleros.extend(datos)

    inicio += limite

# =====================================
# EMPLEADOS
# =====================================

empleados = supabase.table(
    "empleados"
).select("*").execute().data

# =====================================
# ÁREAS
# =====================================

areas = supabase.table(
    "areas"
).select("*").execute().data

areas_dict = {

    a["id"]: a["nombre"]

    for a in areas
}

# =====================================
# ASIGNACIONES
# =====================================

asignaciones = supabase.table(
    "asignaciones"
).select("*") \
 .eq(
    "estado",
    "activa"
 ).execute().data

# =====================================
# NOVEDADES
# =====================================

novedades = supabase.table(
    "novedades"
).select("*") \
 .eq(
    "estado",
    "activa"
 ).execute().data

# =====================================
# DICCIONARIOS
# =====================================

casilleros_dict = {

    c["id"]: c

    for c in casilleros
}

empleados_dict = {

    e["id"]: e

    for e in empleados
}

asignaciones_dict = {

    a["casillero_id"]: a

    for a in asignaciones
}

# =====================================
# ÚLTIMA NOVEDAD
# =====================================

novedades_dict = {}

for n in novedades:

    casillero_id = n["casillero_id"]

    if casillero_id not in novedades_dict:

        novedades_dict[
            casillero_id
        ] = n

    else:

        actual = novedades_dict[
            casillero_id
        ]

        if n["id"] > actual["id"]:

            novedades_dict[
                casillero_id
            ] = n

# =====================================
# DASHBOARD
# =====================================

total = len(casilleros)

disponibles = len([

    c for c in casilleros

    if c["estado"] == "disponible"

])

ocupados = len([

    c for c in casilleros

    if c["estado"] == "ocupado"

])

mantenimiento = len([

    c for c in casilleros

    if c["estado"] == "mantenimiento"

])

# =====================================
# MÉTRICAS
# =====================================

st.subheader("Resumen General")

m1, m2, m3, m4 = st.columns(4)

m1.metric("Total", total)
m2.metric("Disponibles", disponibles)
m3.metric("Ocupados", ocupados)
m4.metric("Mantenimiento", mantenimiento)

# =====================================
# MODAL REGISTRO
# =====================================

@st.dialog("Registrar y Asignar")
def modal_registro():

    empleado_existente = None

    cedula = st.text_input(
        "Cédula",
        max_chars=10
    )

    if len(cedula) == 10:

        consulta = supabase.table(
            "empleados"
        ).select("*") \
         .eq(
            "cedula",
            cedula
         ) \
         .execute()

        if consulta.data:

            empleado_existente = consulta.data[0]

            st.info(
                f"Empleado encontrado: {empleado_existente['nombre_completo']}"
            )

    nombre = st.text_input(
        "Nombre Completo",
        value=
        empleado_existente["nombre_completo"]
        if empleado_existente
        else ""
    )

    lista_generos = [
        "masculino",
        "femenino"
    ]

    genero = st.selectbox(
        "Género",
        lista_generos,
        index=
        lista_generos.index(
            empleado_existente["genero"]
        )
        if empleado_existente
        else 0
    )

    lista_areas = [
        a["nombre"]
        for a in areas
    ]

    area_nombre = st.selectbox(
        "Área",
        lista_areas,
        index=
        lista_areas.index(
            areas_dict[
                empleado_existente["area_id"]
            ]
        )
        if empleado_existente
        else 0
    )

    zona = (
        "hombres"
        if genero == "masculino"
        else "mujeres"
    )

    disponibles = [

        c for c in casilleros

        if (
            c["estado"] == "disponible"
            and
            c["zona"] == zona
        )
    ]

    disponibles = sorted(
        disponibles,
        key=lambda x: x["numero"]
    )

    opciones = {}

    for c in disponibles:

        codigo = (
            f"H{c['numero']}"
            if zona == "hombres"
            else f"F{c['numero']}"
        )

        opciones[
            f"{codigo} | Físico {c['numero']}"
        ] = c["id"]

    if not opciones:

        st.warning(
            "No existen casilleros disponibles"
        )

        return

    casillero_seleccionado = st.selectbox(
        "Casillero",
        list(opciones.keys())
    )

    fecha_entrega = st.date_input(
        "Fecha Entrega"
    )

    if st.button(
        "Guardar Registro",
        use_container_width=True
    ):

        if not cedula.isdigit():

            st.error(
                "La cédula debe contener únicamente números"
            )

            return

        if len(cedula) != 10:

            st.error(
                "La cédula debe tener exactamente 10 dígitos"
            )

            return

        area_id = next(

            a["id"]

            for a in areas

            if a["nombre"] == area_nombre
        )

        if empleado_existente:

            empleado_id = empleado_existente["id"]

        else:

            empleado = supabase.table(
                "empleados"
            ).insert({

                "nombre_completo": nombre,
                "cedula": cedula,
                "genero": genero,
                "area_id": area_id,
                "estado": "activo"

            }).execute()

            empleado_id = empleado.data[0]["id"]

        casillero_id = opciones[
            casillero_seleccionado
        ]

        supabase.table(
            "asignaciones"
        ).insert({

            "empleado_id": empleado_id,
            "casillero_id": casillero_id,
            "fecha_entrega": str(fecha_entrega),
            "estado": "activa"

        }).execute()

        supabase.table(
            "casilleros"
        ).update({

            "estado": "ocupado"

        }).eq(
            "id",
            int(casillero_id)
        ).execute()

        st.success(
            "Registro guardado"
        )

        st.rerun()


# ===========================
# MODAL EDITAR
# ===========================
@st.dialog("Editar Empleado")
def modal_editar(fila):

    empleado = empleados_dict[
        fila["empleado_id"]
    ]

    nombre = st.text_input(
        "Nombre",
        value=empleado["nombre_completo"]
    )

    area_actual = areas_dict[
        empleado["area_id"]
    ]

    lista_areas = [
        a["nombre"]
        for a in areas
    ]

    area_nombre = st.selectbox(
        "Área",
        lista_areas,
        index=lista_areas.index(
            area_actual
        )
    )

    zona = (
        "hombres"
        if empleado["genero"] == "masculino"
        else "mujeres"
    )

    disponibles = [

        c for c in casilleros

        if (
            c["estado"] == "disponible"
            and
            c["zona"] == zona
        )

        or c["id"] == fila["casillero_id"]
    ]

    disponibles = sorted(
        disponibles,
        key=lambda x: x["numero"]
    )

    opciones = {}

    actual = None

    for c in disponibles:

        codigo = (
            f"H{c['numero']}"
            if zona == "hombres"
            else f"F{c['numero']}"
        )

        texto = (
            f"{codigo} | Físico {c['numero']}"
        )

        opciones[texto] = c["id"]

        if c["id"] == fila["casillero_id"]:

            actual = texto

    casillero_nuevo = st.selectbox(
        "Casillero",
        list(opciones.keys()),
        index=list(opciones.keys()).index(
            actual
        )
    )

    if st.button(
        "Guardar Cambios",
        use_container_width=True
    ):

        area_id = next(
            a["id"]
            for a in areas
            if a["nombre"] == area_nombre
        )

        supabase.table(
            "empleados"
        ).update({

            "nombre_completo":
            nombre,

            "area_id":
            area_id

        }).eq(
            "id",
            empleado["id"]
        ).execute()

        nuevo_casillero = int(
            opciones[casillero_nuevo]
        )

        casillero_actual = int(
            fila["casillero_id"]
        )

        asignacion_actual = int(
            fila["asignacion_id"]
        )

        if nuevo_casillero != casillero_actual:

            supabase.table(
                "casilleros"
            ).update({

                "estado":
                "disponible"

            }).eq(
                "id",
                casillero_actual
            ).execute()

            supabase.table(
                "casilleros"
            ).update({

                "estado":
                "ocupado"

            }).eq(
                "id",
                nuevo_casillero
            ).execute()

            supabase.table(
                "asignaciones"
            ).update({

                "casillero_id":
                nuevo_casillero

            }).eq(
                "id",
                asignacion_actual
            ).execute()

        st.success(
            "Actualizado correctamente"
        )

        st.rerun()
# =====================================
#MODAL NOVEDADES
# =====================================

@st.dialog("Registrar Novedad")
def modal_novedad(fila):

    descripcion = st.text_area(
        "Descripción"
    )

    enviar_mantenimiento = st.checkbox(
        "Enviar casillero a mantenimiento"
    )

    if st.button(
        "Guardar Novedad",
        use_container_width=True
    ):

        if not descripcion.strip():

            st.error(
                "Ingrese una descripción"
            )

            return

        supabase.table(
            "novedades"
        ).insert({

            "casillero_id":
            int(fila["casillero_id"]),

            "descripcion":
            descripcion,

            "estado":
            "activa"

        }).execute()

        if enviar_mantenimiento:

            supabase.table(
                "casilleros"
            ).update({

                "estado":
                "mantenimiento"

            }).eq(
                "id",
                int(fila["casillero_id"])
            ).execute()

        st.success(
            "Novedad registrada"
        )

        st.rerun()

# =====================================
#MODAL HISTORIAL
# =====================================

# =====================================
# MODAL HISTORIAL
# =====================================

@st.dialog("Historial de Novedades")
def modal_historial(fila):

    historial = supabase.table(
        "novedades"
    ).select("*") \
     .eq(
        "casillero_id",
        int(fila["casillero_id"])
     ) \
     .order(
        "id",
        desc=True
     ) \
     .execute()

    if not historial.data:

        st.info(
            "No existen novedades"
        )

        return

    for n in historial.data:

        fecha = n["created_at"][:10]

        st.write(
        f"📅 {fecha}"
        )

        st.write(
            f"• {n['descripcion']}"
        )

# =====================================
#BOTÓN REGISTRAR
# =====================================

if st.button(
    "➕ Registrar y Asignar"
):
    modal_registro()


# =====================================
# TABLA
# =====================================

tabla = []

# =====================================
# ORDENAR CASILLEROS
# =====================================

casilleros = sorted(

    casilleros,

    key=lambda x: (
        x["zona"],
        x["numero"]
    )
)

# =====================================
# RECORRER
# =====================================

for c in casilleros:

    asignacion = asignaciones_dict.get(
    c["id"]
)

    empleado = None

    fecha_entrega = ""

    if asignacion:

        empleado = empleados_dict.get(
            asignacion["empleado_id"]
        )

        fecha_entrega = asignacion[
            "fecha_entrega"
        ]

    # =====================================
    # VISUAL
    # =====================================

    if c["zona"] == "hombres":

        visual = f"H{c['numero']}"

    else:

        visual = f"F{c['numero']}"

    # =====================================
    # ÁREA
    # =====================================

    area = ""

    if empleado:

        area = areas_dict.get(
            empleado["area_id"],
            ""
        )

    # =====================================
    # NOVEDAD
    # =====================================

    novedad = ""

    if c["id"] in novedades_dict:

        novedad = novedades_dict[
            c["id"]
        ]["descripcion"]

    # =====================================
    # TABLA
    # =====================================

    tabla.append({

        "casillero_id":
        c["id"],

        "asignacion_id":
        asignacion["id"]
        if asignacion
        else None,

        "empleado_id":
        empleado["id"]
        if empleado
        else None,

        "Cédula":
        empleado["cedula"]
        if empleado
        else "",

        "Nombre":
        empleado["nombre_completo"]
        if empleado
        else "",

        "Área":
        area,

        "Casillero Visual":
        visual,

        "Casillero Físico":
        c["numero"],

        "Fecha Entrega":
        fecha_entrega,

        "Estado":
        c["estado"],

        "Novedad":
        novedad
    })

# =====================================
# DATAFRAME
# =====================================

df = pd.DataFrame(tabla)

# =====================================
# EXPORTAR NOVEDADES
# =====================================

datos_exportacion = []

for n in novedades:

    casillero = casilleros_dict.get(
        n["casillero_id"]
    )

    if not casillero:
        continue

    visual = (
        f"H{casillero['numero']}"
        if casillero["zona"] == "hombres"
        else f"F{casillero['numero']}"
    )

    datos_exportacion.append({

        "Casillero":
        visual,

        "Estado":
        casillero["estado"],

        "Novedad":
        n["descripcion"],

        "Fecha":
        n["created_at"][:10]

    })

df_novedades = pd.DataFrame(
    datos_exportacion
)

excel_buffer = BytesIO()

with pd.ExcelWriter(
    excel_buffer,
    engine="openpyxl"
) as writer:

    df_novedades.to_excel(
        writer,
        index=False,
        sheet_name="Novedades"
    )

excel_buffer.seek(0) 

# =====================================
# FILTROS
# =====================================

st.download_button(

    "📥 Exportar Novedades",

    data=excel_buffer,

    file_name="novedades_casilleros.xlsx",

    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

)

st.subheader("Filtros")

f1, f2 = st.columns(2)

buscar = f1.text_input(
    "Buscar"
)

estado_filtro = f2.selectbox(
    "Estado",
    [
        "Todos",
        "ocupado",
        "disponible",
        "mantenimiento"
    ]
)

if buscar:

    df = df[
        df.astype(str)
        .apply(
            lambda row:
            row.str.contains(
                buscar,
                case=False
            ).any(),
            axis=1
        )
    ]

if estado_filtro != "Todos":

    df = df[
        df["Estado"] == estado_filtro
    ]

# =====================================
# PAGINACIÓN
# =====================================

total_paginas = math.ceil(
    len(df) / REGISTROS_POR_PAGINA
)

pagina = st.number_input(
    "Página",
    min_value=1,
    max_value=max(
        total_paginas,
        1
    ),
    value=1
)

inicio = (
    (pagina - 1)
    * REGISTROS_POR_PAGINA
)

fin = inicio + REGISTROS_POR_PAGINA

df_pagina = df.iloc[
    inicio:fin
]

# =====================================
# ENCABEZADOS
# =====================================

st.subheader("Casilleros")

h = st.columns(
    [1,2,1,1,1,1,1,1,2]
)

h[0].markdown("**Cédula**")
h[1].markdown("**Nombre**")
h[2].markdown("**Área**")
h[3].markdown("**Cas. Visual**")
h[4].markdown("**Cas. Físico**")
h[5].markdown("**Fecha Entrega**")
h[6].markdown("**Estado**")
h[7].markdown("**Novedad**")
h[8].markdown("**Acciones**")

# =====================================
# FILAS
# =====================================

for i, fila in df_pagina.iterrows():

    with st.container(border=True):

        cols = st.columns(
            [1,2,1,1,1,1,1,1,2]
        )

        cols[0].write(
            fila["Cédula"]
        )

        cols[1].write(
            fila["Nombre"]
        )

        cols[2].write(
            fila["Área"]
        )

        cols[3].success(
            fila["Casillero Visual"]
        )

        cols[4].info(
            str(
                fila["Casillero Físico"]
            )
        )

        cols[5].write(
            str(
                fila["Fecha Entrega"]
            )
        )

        if fila["Estado"] == "ocupado":

            cols[6].error(
                "Ocupado"
            )

        elif fila["Estado"] == "disponible":

            cols[6].success(
                "Disponible"
            )

        else:

            cols[6].warning(
                "Mantenimiento"
            )

        cols[7].write(
            fila["Novedad"]
        )
        with cols[8]:

          c1, c2, c3, c4 = st.columns(4)

# =====================================
# EDITAR
# =====================================

        if pd.notna(
            fila["empleado_id"]
        ):

            if c1.button(
              "✏️",
              key=f"editar_{i}"
        ):

              modal_editar(fila)

        else:

              c1.write("")

# =====================================
# NOVEDAD
# =====================================

        if c2.button(
          "➕",
          key=f"novedad_{i}"
        ):

          modal_novedad(fila)

# =====================================
# HISTORIAL
# =====================================

        if c3.button(
          "📋",
          key=f"historial_{i}"
        ):

          modal_historial(fila)

# =====================================
# LIBERAR / HABILITAR
# =====================================

        if pd.notna(
            fila["asignacion_id"]
        ):

            if c4.button(
                "🔓",
                key=f"liberar_{i}"
            ):

                supabase.table(
                    "asignaciones"
                ).update({

                    "estado":
                    "finalizada"

                }).eq(
                    "id",
                    int(fila["asignacion_id"])
                ).execute()

                supabase.table(
                    "casilleros"
                ).update({

                    "estado":
                    "disponible"

                }).eq(
                    "id",
                    int(fila["casillero_id"])
                ).execute()

                st.rerun()

        else:

            if fila["Estado"] == "mantenimiento":

                if c4.button(
                    "✅",
                    key=f"habilitar_{i}"
                ):

                    casillero_id = int(
                        fila["casillero_id"]
                    )

                    supabase.table(
                        "casilleros"
                    ).update({

                        "estado":
                        "disponible"

                    }).eq(
                        "id",
                        casillero_id
                    ).execute()

                    supabase.table(
                        "novedades"
                    ).update({

                        "estado":
                        "cerrada"

                    }).eq(
                        "casillero_id",
                        casillero_id
                    ).eq(
                        "estado",
                        "activa"
                    ).execute()

                    st.rerun()

            else:

                c4.write("")





# =====================================
# FOOTER
# =====================================

st.write(
    f"Página {pagina} de {total_paginas}"
)
