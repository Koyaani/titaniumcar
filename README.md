# Titanium Car
---
### Un projet fait à l'IMT Lille Douai
#### Novembre 2019

Ce dépot contient tous les notebooks et programmes faits durant le projet.

## Le projet
---

L'objectif du projet s'insprire de celui du concours **IronCar** :

> Transformer une voiture téléguidée en voiture autonome pour effectuer le plus rapidement possible un tour du circuit.

## Le sommairea
1. [Le contexte](#le-contexte)
2. [Installation](#installation)
3. [Les technos](#les-technos)
4. [La structure](#la-structure)
4. [Les auteurs](#les-auteurs)


## Le contexte
---

TitaniumCar a été un projet d'initiation au deep learning et de découverte des différentes librairies de la data science. Il nous a permis de pratiquer toutes les étapes qu'un projet de data science peut avoir : 
 * Définition de la problématique
 * Conception
 * Création du dataset
 * Apprentissage
 * Tests
 * Déploiment


Le projet ne durant qu'un seul mois, le code a du être restructuré par la suite. Le code destiné à être deployer sur la voiture pourrait contenir des bugs. Le reste du dépot a été testé.


## Installation
---
Pour pouvoir expérimenter et utiliser directement le code, l'environnement Conda a été exporté. L'installation se fait simplement avec :

```bash
conda create -n titaniumcar python=3.7
conda env update --file environment.yml
```

Cette méthode est plus simple à mettre en place que celle décrite dans le rapport pdf.

Les données étant volumineuses doivent être téléchargées séparement à cette adresse : 
[cdn.facchini.fr/92J7pN7jl8yQTZfp/data_titaniumcar.zip](https://cdn.facchini.fr/92J7pN7jl8yQTZfp/data_titaniumcar.zip)

## Les technos
---
Le langage utilisé pour l'ensemble du projet est python 3.7. Ensuite les principales technos utilisées sont :
 * Pytorch
 * Tensorflow
 * Pygame
 * OpenCV
 * Numpy
 * Picamera et Adafruit

## La structure
---
Le projet a été séparé en 5 parties :

 * **Experimentations** : Tous les tests que nous avons effectué mais qui n'ont pas été utilisés dans la version finale du projet
 * **Processes** : Les notebooks pour tester les modèles de prédictions
 * **Titaniumcar** : Code source pour la conduite de la voiture 
 * **Labeling** : Méthodes pour la labélisation des photos prises pas la voiture
 * (**Data** : comprends le dataset, les vidéos et les tests, doit être téléchargé)
 
Le dépot contient aussi le rapport complet du projet au format pdf.

## Les auteurs
---
La partie logicielle a été conçue par :

* **Pierre Montroeul**
* **Antone Facchini**
