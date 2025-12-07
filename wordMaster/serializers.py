from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PuzzleSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = WordPuzzle
        fields = ["id", "title", "start_date", "end_date", "status", "banner"]

    def get_status(self, obj):
        
        now = timezone.now()

        if obj.status=="active":
            return "active"
        return "inactive"


class WordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Word
        fields = ["id", "text", "hint", "difficulty", "is_active"]



class PuzzleWordSerializer(serializers.ModelSerializer):
    word = WordSerializer()

    class Meta:
        model = WordPuzzle
        fields = ["id", "puzzle", "word", "order"]
