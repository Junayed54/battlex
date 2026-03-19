from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class PuzzleSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = WordPuzzle
        fields = '__all__'

    def get_status(self, obj):
        
        now = timezone.now()

        if obj.status=="active":
            return "active"
        return "inactive"


class WordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Word
        fields = ["id", "text", "hint", "difficulty"]



class PuzzleWordSerializer(serializers.ModelSerializer):
    word = WordSerializer()

    class Meta:
        model = WordPuzzle
        fields = ["id", "puzzle", "word", "order"]




class WordExcelUploadSerializer(serializers.Serializer):
    puzzle_id = serializers.IntegerField()
    file = serializers.FileField()



class RewardBalanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserRewardBalance
        fields = ["total_points"]


class RewardEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = RewardEvent
        fields = [
            "id",
            "points",
            "reason",
            "created_at"
        ]


class RewardClaimSerializer(serializers.ModelSerializer):

    class Meta:
        model = RewardClaim
        fields = [
            "id",
            "points_used",
            "amount",
            "status",
            "created_at"
        ]