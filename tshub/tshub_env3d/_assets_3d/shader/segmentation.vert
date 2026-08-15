#version 330 core
uniform mat4 p3d_ModelViewProjectionMatrix;
in vec4 p3d_Vertex;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
}
