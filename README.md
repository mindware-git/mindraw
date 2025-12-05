# mindraw
Compiler for Generative AI

## Problem
1. AI generated video is hard to control.  
2. Consistency between frames.

## Idea
1. Use render engine like source code.  
2. Convert between AI and render data.


## 수학적 정리

- 렌더링 함수 R:  
$$  
I_i = R(S_i)  
$$  

여기서 $ R $은 상태 $ S_i $를 입력으로 받아 이미지 $ I_i $를 출력하는 결정론적 함수입니다.  

- 명령어 또는 조작 함수:  
$$  
C(S_i, P_i) = \{ \text{명령어 또는 조작} \}  
$$  
여기서 $ C $는 상태 $ S_i $와 프롬프트 $ P_i $를 입력으로 받아, 다음 이미지 $ I_{i+1} $를 생성하기 위한 명령어 또는 조작을 출력합니다.  

- 렌더링 함수와 결합:  
$$  
I_{i+1} = R(S_i, C(S_i, P_i))  
$$

- 이제 여기서 C를 구하는 것이 목표입니다.
- 즉 다음 이미지를 주었을때, 프롬프트와 현재 이미지를 통해 C를 구해야 합니다.

딥러닝을 통해 충분히 학습 할 수 있음.
그러나 이미지의 종류를 많이 좁혀둬야지 R의 복잡도를 줄일 수 있습니다.
예를들어 sketch 전용 C를 만든다던지 모델링 전용 C를 만든다던지 등등.

C를 정확히 구할 수 있다면 목표로 한 컴파일러처럼 어떤 이미지에서 다음 이미지에 대한 프롬프트만 넣어도 다음 이미지를 만들 수 있습니다.