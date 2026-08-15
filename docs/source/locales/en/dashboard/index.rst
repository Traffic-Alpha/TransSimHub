Mesoscopic Congestion Dashboard
=================================

The third visualization path in TransSimHub. The three views answer different questions:

.. list-table::
  :header-rows: 1

  * - View
    - Entry point
    - Question it answers
  * - Microscopic
    - ``TshubEnvironment.render(mode='sumo_gui')`` / ``use_gui=True``
    - What is each individual vehicle doing (small area)
  * - **Mesoscopic**
    - ``tshub.visualization.meso``
    - **Where is the network congested, and how does it spread**
  * - 3D / aerial
    - ``Tshub3DEnvironment`` + ``sensor_config``
    - What does a camera on a UAV / vehicle / junction see

All three can run in the same simulation.


Data source
~~~~~~~~~~~~~

The dashboard only consumes three keys of ``obs`` and does **not** depend on the
environment, so any loop able to produce that data can drive it:

- ``obs['lane_shape']`` — static lane geometry (``is_map_builder_initialized=True``), used to draw the network;
- ``obs['edge_state']`` — edge-level traffic state (``is_edge_builder_initialized=True``), used for colouring;
- ``obs['lane_state']`` — lane-level traffic state (``is_lane_builder_initialized=True``), used when drilling down.

The congestion index is ``speed_relative = mean_speed / max_speed``, clamped to
[0, 1] — the same quantity as ``speedRelative`` in SUMO's ``meandata`` output.
1 means free flow, 0 means fully stopped.

.. note::

   Do not confuse the two "lane" keys: ``obs['lane_shape']`` is the static
   *geometry* (from ``tshub/map/``), ``obs['lane_state']`` is the dynamic
   *traffic state* (from ``tshub/lane/``). They are joined on ``lane_id``.


Usage
~~~~~~~~~~~~~

.. code-block:: python

    from tshub.visualization.meso import DashboardServer, build_static_payload, build_frame_payload

    dashboard = DashboardServer(port=8910)
    url = dashboard.start()          # background thread, never blocks the simulation

    obs = tshub_env.reset()
    static_payload = build_static_payload(obs)
    dashboard.set_static(static_payload)   # network geometry, sent once

    while not done:
        obs, _, infos, done = tshub_env.step(actions={})
        dashboard.push(build_frame_payload(
            sim_time=infos['step_time'], obs=obs, static_payload=static_payload,
        ))

    dashboard.stop()

Then open ``url`` (``http://127.0.0.1:8910`` by default). Runnable examples live in
`examples/dashboard <https://github.com/Traffic-Alpha/TransSimHub/tree/main/examples/dashboard>`_.


Implementation notes
~~~~~~~~~~~~~~~~~~~~~~

- Standard library only (``http.server`` + SSE, no flask/fastapi) and **no vendored
  JS library** — the network map is a hand-written Canvas renderer, because SUMO
  networks are in Cartesian metres rather than lon/lat.
- Per-frame congestion values are quantized to ``uint8`` and base64-encoded, keeping
  a 2000-edge network at a few KB per frame. Round-trip error stays within half a
  quantization step (≈0.002), which affects neither colouring nor ranking.
- ``push()`` never blocks the simulation: each browser gets a bounded queue and the
  oldest frame is dropped when it is full, so a slow or closed browser cannot stall
  the run.
