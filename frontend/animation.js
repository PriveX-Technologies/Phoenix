import * as THREE from "three";

export class PhoenixAnimator {

    constructor(model) {

        this.model = model;

        this.headBone = null;

        this.isTalking = false;
        this.currentEmotion = "neutral";

        this.mouseX = 0;
        this.mouseY = 0;

        this.clock = new THREE.Clock();

        this.findBones();
        this.setupMouseTracking();
    }

    findBones() {

        this.model.traverse((obj) => {

            if (
                obj.isBone &&
                obj.name.toLowerCase().includes("head")
            ) {
                this.headBone = obj;
                console.log("✅ Head Bone:", obj.name);
            }

        });

    }

    setupMouseTracking() {

        window.addEventListener("mousemove", (e) => {

            this.mouseX =
                (e.clientX / window.innerWidth) * 2 - 1;

            this.mouseY =
                (e.clientY / window.innerHeight) * 2 - 1;

        });

    }

    setEmotion(emotion) {
        this.currentEmotion = emotion;
    }

    startTalking() {
        this.isTalking = true;
    }

    stopTalking() {
        this.isTalking = false;
    }

    update() {

        const t = this.clock.getElapsedTime();

        // breathing
        this.model.position.y =
            Math.sin(t * 1.5) * 0.03;

        // head follow mouse
        if (this.headBone) {

            this.headBone.rotation.y =
                this.mouseX * 0.25;

            this.headBone.rotation.x =
                -this.mouseY * 0.15;

        }

        // talking motion
        if (this.isTalking && this.headBone) {

            this.headBone.rotation.y +=
                Math.sin(t * 12) * 0.02;

        }

        // emotions
        switch (this.currentEmotion) {

            case "happy":

                this.model.rotation.z =
                    Math.sin(t * 2) * 0.02;

                break;

            case "sad":

                this.model.rotation.z = 0;

                break;

            case "angry":

                this.model.rotation.y =
                    Math.sin(t * 4) * 0.03;

                break;

            default:

                this.model.rotation.z = 0;

        }

    }

}