#version 330 core
// 每个节点通过 setShaderInput("label_color", ...) 提供其语义类标签色
uniform vec4 label_color;
out vec4 fragColor;
void main() {
    fragColor = label_color;
}
